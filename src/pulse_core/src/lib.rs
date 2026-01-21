use pyo3::prelude::*;
use pyo3::types::PyDict;
use sysinfo::{System, Networks, Disks};
use std::sync::Mutex;
use std::cmp::Ordering;

struct SysState {
    system: System,
    networks: Networks,
    disks: Disks,
}

// Global system state to avoid re-initializing
static STATE: Mutex<Option<SysState>> = Mutex::new(None);

fn get_state() -> std::sync::MutexGuard<'static, Option<SysState>> {
    let mut guard = STATE.lock().unwrap();
    if guard.is_none() {
        let mut system = System::new_all();
        system.refresh_all();
        let networks = Networks::new_with_refreshed_list();
        let disks = Disks::new_with_refreshed_list();
        *guard = Some(SysState { system, networks, disks });
    }
    guard
}

#[pyfunction]
fn init_system() {
    let mut guard = get_state();
    if let Some(state) = guard.as_mut() {
        state.system.refresh_all();
        state.networks.refresh_list();
        state.disks.refresh_list();
    }
}

#[pyfunction]
fn get_cpu_percents() -> PyResult<Vec<f32>> {
    let mut guard = get_state();
    let state = guard.as_mut().unwrap();
    state.system.refresh_cpu();
    Ok(state.system.cpus().iter().map(|cpu| cpu.cpu_usage()).collect())
}

#[pyfunction]
fn get_memory_info(py: Python<'_>) -> PyResult<PyObject> {
    let mut guard = get_state();
    let state = guard.as_mut().unwrap();
    state.system.refresh_memory();
    
    let dict = PyDict::new(py);
    dict.set_item("total", state.system.total_memory())?;
    dict.set_item("used", state.system.used_memory())?;
    dict.set_item("free", state.system.free_memory())?;
    dict.set_item("available", state.system.available_memory())?;
    
    dict.set_item("swap_total", state.system.total_swap())?;
    dict.set_item("swap_used", state.system.used_swap())?;
    dict.set_item("swap_free", state.system.free_swap())?;
    
    Ok(dict.to_object(py))
}

#[pyfunction]
fn get_process_list(
    py: Python<'_>, 
    sort_by: Option<String>, 
    limit: Option<usize>
) -> PyResult<Vec<PyObject>> {
    let mut guard = get_state();
    let state = guard.as_mut().unwrap();
    state.system.refresh_processes();
    
    let mut proc_vec: Vec<PyObject> = Vec::new();
    
    struct ProcData {
        pid: u32,
        name: String,
        cpu: f32,
        mem: u64,
        user: String,
        status: String,
    }
    
    let mut data_vec: Vec<ProcData> = state.system.processes().iter().map(|(pid, process)| {
        ProcData {
            pid: pid.as_u32(),
            name: process.name().to_string(),
            cpu: process.cpu_usage(),
            mem: process.memory(),
            user: process.user_id().map(|u| u.to_string()).unwrap_or_else(|| "?".to_string()),
            status: format!("{:?}", process.status()),
        }
    }).collect();

    if let Some(key) = sort_by {
        match key.as_str() {
            "cpu" => data_vec.sort_unstable_by(|a, b| b.cpu.partial_cmp(&a.cpu).unwrap_or(Ordering::Equal)),
            "mem" => data_vec.sort_unstable_by(|a, b| b.mem.cmp(&a.mem)),
            _ => {}
        }
    }
    
    let count = limit.unwrap_or(data_vec.len()).min(data_vec.len());
    
    for p in data_vec.into_iter().take(count) {
        let dict = PyDict::new(py);
        dict.set_item("pid", p.pid)?;
        dict.set_item("name", p.name)?;
        dict.set_item("cpu_percent", p.cpu)?;
        dict.set_item("memory_info", p.mem)?; 
        dict.set_item("status", p.status)?;
        dict.set_item("username", p.user)?;
        proc_vec.push(dict.to_object(py));
    }

    Ok(proc_vec)
}

#[pyfunction]
fn get_network_stats(py: Python<'_>) -> PyResult<PyObject> {
    let mut guard = get_state();
    let state = guard.as_mut().unwrap();
    state.networks.refresh();
    
    let mut total_received = 0;
    let mut total_transmitted = 0;
    for (_interface_name, data) in &state.networks {
        total_received += data.received();
        total_transmitted += data.transmitted();
    }
    
    let dict = PyDict::new(py);
    dict.set_item("bytes_recv", total_received)?;
    dict.set_item("bytes_sent", total_transmitted)?;
    Ok(dict.to_object(py))
}

#[pyfunction]
fn get_disk_info(py: Python<'_>) -> PyResult<Vec<PyObject>> {
    let mut guard = get_state();
    let state = guard.as_mut().unwrap();
    state.disks.refresh();
    
    let mut disks = Vec::new();
    for disk in &state.disks {
        let dict = PyDict::new(py);
        dict.set_item("mount_point", disk.mount_point().to_string_lossy())?;
        dict.set_item("name", disk.name().to_string_lossy())?;
        dict.set_item("file_system", disk.file_system().to_string_lossy())?;
        dict.set_item("total_space", disk.total_space())?;
        dict.set_item("available_space", disk.available_space())?;
        dict.set_item("is_removable", disk.is_removable())?;
        
        disks.push(dict.to_object(py));
    }
    Ok(disks)
}

#[pymodule]
fn pulse_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(init_system, m)?)?;
    m.add_function(wrap_pyfunction!(get_cpu_percents, m)?)?;
    m.add_function(wrap_pyfunction!(get_memory_info, m)?)?;
    m.add_function(wrap_pyfunction!(get_process_list, m)?)?;
    m.add_function(wrap_pyfunction!(get_network_stats, m)?)?;
    m.add_function(wrap_pyfunction!(get_disk_info, m)?)?;
    Ok(())
}
