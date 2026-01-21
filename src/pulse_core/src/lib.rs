use pyo3.prelude::*;
use pyo3.types::PyDict;
use sysinfo::{CpuExt, DiskExt, NetworkExt, ProcessExt, System, SystemExt};
use std::sync::Mutex;
use std::cmp::Ordering;

// Global system state to avoid re-initializing
static SYSTEM: Mutex<Option<System>> = Mutex::new(None);

/// Initialize the system monitor
#[pyfunction]
fn init_system() {
    let mut guard = SYSTEM.lock().unwrap();
    if guard.is_none() {
        let mut sys = System::new_all();
        sys.refresh_all();
        *guard = Some(sys);
    } else {
        guard.as_mut().unwrap().refresh_all();
    }
}

/// Get CPU usage percentage for all cores
#[pyfunction]
fn get_cpu_percents() -> PyResult<Vec<f32>> {
    let mut guard = SYSTEM.lock().unwrap();
    if let Some(sys) = guard.as_mut() {
        sys.refresh_cpu();
        Ok(sys.cpus().iter().map(|cpu| cpu.cpu_usage()).collect())
    } else {
        drop(guard);
        init_system();
        get_cpu_percents()
    }
}

/// Get Memory usage statistics
#[pyfunction]
fn get_memory_info(py: Python<'_>) -> PyResult<PyObject> {
    let mut guard = SYSTEM.lock().unwrap();
    if let Some(sys) = guard.as_mut() {
        sys.refresh_memory();
        
        let dict = PyDict::new(py);
        dict.set_item("total", sys.total_memory())?;
        dict.set_item("used", sys.used_memory())?;
        dict.set_item("free", sys.free_memory())?;
        dict.set_item("available", sys.available_memory())?;
        
        dict.set_item("swap_total", sys.total_swap())?;
        dict.set_item("swap_used", sys.used_swap())?;
        dict.set_item("swap_free", sys.free_swap())?;
        
        Ok(dict.to_object(py))
    } else {
        drop(guard);
        init_system();
        get_memory_info(py)
    }
}

/// Get list of running processes with optional sorting and limiting
#[pyfunction]
fn get_process_list(
    py: Python<'_>, 
    sort_by: Option<String>, 
    limit: Option<usize>
) -> PyResult<Vec<PyObject>> {
    let mut guard = SYSTEM.lock().unwrap();
    if let Some(sys) = guard.as_mut() {
        sys.refresh_processes();
        
        let mut processes: Vec<PyObject> = Vec::new();
        
        // Temporarily collect data for sorting
        struct ProcData {
            pid: u32,
            name: String,
            cpu: f32,
            mem: u64,
            user: String,
            status: String,
        }
        
        let mut proc_vec: Vec<ProcData> = sys.processes().iter().map(|(pid, process)| {
            ProcData {
                pid: pid.as_u32(),
                name: process.name().to_string(),
                cpu: process.cpu_usage(),
                mem: process.memory(),
                user: process.user_id().map(|u| u.to_string()).unwrap_or_else(|| "?".to_string()),
                status: format!("{:?}", process.status()),
            }
        }).collect();

        // Native Sorting
        if let Some(key) = sort_by {
            match key.as_str() {
                "cpu" => proc_vec.sort_unstable_by(|a, b| b.cpu.partial_cmp(&a.cpu).unwrap_or(Ordering::Equal)),
                "mem" => proc_vec.sort_unstable_by(|a, b| b.mem.cmp(&a.mem)),
                _ => {}
            }
        }
        
        // Limiting
        let count = limit.unwrap_or(proc_vec.len()).min(proc_vec.len());
        
        for p in proc_vec.into_iter().take(count) {
            let dict = PyDict::new(py);
            dict.set_item("pid", p.pid)?;
            dict.set_item("name", p.name)?;
            dict.set_item("cpu_percent", p.cpu)?;
            dict.set_item("memory_info", p.mem)?; 
            dict.set_item("status", p.status)?;
            dict.set_item("username", p.user)?;
            processes.push(dict.to_object(py));
        }

        Ok(processes)
    } else {
        drop(guard);
        init_system();
        get_process_list(py, sort_by, limit)
    }
}

/// Get Global Network IO Counters
#[pyfunction]
fn get_network_stats(py: Python<'_>) -> PyResult<PyObject> {
    let mut guard = SYSTEM.lock().unwrap();
    if let Some(sys) = guard.as_mut() {
        sys.refresh_networks();
        
        let mut total_received = 0;
        let mut total_transmitted = 0;
        for (_interface_name, data) in sys.networks() {
            total_received += data.received();
            total_transmitted += data.transmitted();
        }
        
        let dict = PyDict::new(py);
        dict.set_item("bytes_recv", total_received)?;
        dict.set_item("bytes_sent", total_transmitted)?;
        Ok(dict.to_object(py))
    } else {
        drop(guard);
        init_system();
        get_network_stats(py)
    }
}

/// Get Disk Information (Mounts + Usage)
#[pyfunction]
fn get_disk_info(py: Python<'_>) -> PyResult<Vec<PyObject>> {
    let mut guard = SYSTEM.lock().unwrap();
    if let Some(sys) = guard.as_mut() {
        sys.refresh_disks();
        
        let mut disks = Vec::new();
        for disk in sys.disks() {
            let dict = PyDict::new(py);
            // Matches storage.py naming
            dict.set_item("mount_point", disk.mount_point().to_string_lossy())?;
            dict.set_item("name", disk.name().to_string_lossy())?;
            dict.set_item("file_system", disk.file_system().to_string_lossy())?;
            dict.set_item("total_space", disk.total_space())?;
            dict.set_item("available_space", disk.available_space())?;
            dict.set_item("is_removable", disk.is_removable())?;
            
            disks.push(dict.to_object(py));
        }
        Ok(disks)
    } else {
        drop(guard);
        init_system();
        get_disk_info(py)
    }
}

/// A Python module implemented in Rust.
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
