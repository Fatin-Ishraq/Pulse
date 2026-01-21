use pyo3.prelude::*;
use pyo3.types::PyDict;
use sysinfo::{CpuRefreshKind, MemoryRefreshKind, RefreshKind, System};
use std::sync::Mutex;

// Global system state to avoid re-initializing
struct PulseSystem {
    sys: System,
}

// Wrap in a Mutex for thread safety (Python releases GIL, multiple threads might access)
static SYSTEM: Mutex<Option<PulseSystem>> = Mutex::new(None);

/// Initialize the system monitor
#[pyfunction]
fn init_system() -> PyResult<()> {
    let mut guard = SYSTEM.lock().unwrap();
    if guard.is_none() {
        let sys = System::new_with_specifics(
            RefreshKind::new()
                .with_cpu(CpuRefreshKind::everything())
                .with_memory(MemoryRefreshKind::everything()),
        );
        *guard = Some(PulseSystem { sys });
    }
    Ok(())
}

/// Get CPU usage percentage for all cores
#[pyfunction]
fn get_cpu_percents() -> PyResult<Vec<f32>> {
    let mut guard = SYSTEM.lock().unwrap();
    if let Some(pulse) = guard.as_mut() {
        // Refresh CPU data
        pulse.sys.refresh_cpu();
        
        let cpus = pulse.sys.cpus();
        let mut usages = Vec::with_capacity(cpus.len());
        for cpu in cpus {
            usages.push(cpu.cpu_usage());
        }
        Ok(usages)
    } else {
        drop(guard);
        let _ = init_system();
        get_cpu_percents()
    }
}

/// Get Memory usage statistics
#[pyfunction]
fn get_memory_info(py: Python<'_>) -> PyResult<PyObject> {
    let mut guard = SYSTEM.lock().unwrap();
    if let Some(pulse) = guard.as_mut() {
        pulse.sys.refresh_memory();
        
        let dict = PyDict::new(py);
        dict.set_item("total", pulse.sys.total_memory())?;
        dict.set_item("used", pulse.sys.used_memory())?;
        dict.set_item("free", pulse.sys.free_memory())?; // sysinfo 0.30 has free_memory
        dict.set_item("available", pulse.sys.available_memory())?;
        
        dict.set_item("swap_total", pulse.sys.total_swap())?;
        dict.set_item("swap_used", pulse.sys.used_swap())?;
        dict.set_item("swap_free", pulse.sys.free_swap())?;
        
        Ok(dict.to_object(py))
    } else {
        drop(guard);
        let _ = init_system();
        get_memory_info(py)
    }
}

/// Get list of running processes
#[pyfunction]
fn get_process_list(py: Python<'_>) -> PyResult<Vec<PyObject>> {
    let mut guard = SYSTEM.lock().unwrap();
    if let Some(pulse) = guard.as_mut() {
        pulse.sys.refresh_processes();
        
        let mut processes = Vec::new();
        for (pid, process) in pulse.sys.processes() {
            let dict = PyDict::new(py);
            dict.set_item("pid", pid.as_u32())?;
            dict.set_item("name", process.name())?;
            dict.set_item("cpu_percent", process.cpu_usage())?;
            dict.set_item("memory_percent", 0.0)?; // sysinfo doesn't give straightforward % yet easily without total
            dict.set_item("memory_info", process.memory())?; // bytes
            dict.set_item("status", format!("{:?}", process.status()))?;
            dict.set_item("username", process.user_id().map(|u| u.to_string()).unwrap_or_default())?;
            
            processes.push(dict.to_object(py));
        }
        Ok(processes)
    } else {
        drop(guard);
        let _ = init_system();
        get_process_list(py)
    }
}

/// A Python module implemented in Rust.
#[pymodule]
fn pulse_core(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(init_system, m)?)?;
    m.add_function(wrap_pyfunction!(get_cpu_percents, m)?)?;
    m.add_function(wrap_pyfunction!(get_memory_info, m)?)?;
    m.add_function(wrap_pyfunction!(get_process_list, m)?)?;
    Ok(())
}
