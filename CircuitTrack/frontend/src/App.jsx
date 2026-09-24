import React, { useEffect, useState } from "react";

const API = "/api";
const statuses = ["Received", "Diagnosing", "Waiting for Parts", "Repairing", "Completed"];

async function api(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${response.status}`);
  }
  return response.json();
}

function Metric({ label, value }) {
  return (
    <div className="card">
      <div className="muted">{label}</div>
      <div className="metric">{value}</div>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("Dashboard");
  const [dashboard, setDashboard] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [devices, setDevices] = useState([]);
  const [repairs, setRepairs] = useState([]);
  const [parts, setParts] = useState([]);
  const [technicians, setTechnicians] = useState([]);
  const [deviceTypes, setDeviceTypes] = useState([]);
  const [selectedRepair, setSelectedRepair] = useState(null);
  const [error, setError] = useState("");

  async function refresh() {
    try {
      setError("");
      const [dash, cust, dev, rep, prt, tech, types] = await Promise.all([
        api("/dashboard"),
        api("/customers"),
        api("/devices"),
        api("/repairs"),
        api("/parts"),
        api("/technicians"),
        api("/device-types")
      ]);
      setDashboard(dash);
      setCustomers(cust);
      setDevices(dev);
      setRepairs(rep);
      setParts(prt);
      setTechnicians(tech);
      setDeviceTypes(types);
    } catch (e) {
      setError(e.message);
    }
  }

  async function openRepair(id) {
    try {
      setSelectedRepair(await api(`/repairs/${id}`));
      setTab("Repair Detail");
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => { refresh(); }, []);

  return (
    <div className="app">
      <header>
        <div>
          <h1>CircuitTrack</h1>
          <div className="muted">Electronics Repair Management System</div>
        </div>
        <button onClick={refresh}>Refresh</button>
      </header>

      <nav>
        {["Dashboard","Customers","Devices","Repairs","Parts","Technicians"].map(name => (
          <button
            key={name}
            className={tab === name ? "active" : ""}
            onClick={() => setTab(name)}
          >
            {name}
          </button>
        ))}
      </nav>

      {error && <div className="error">{error}</div>}

      <main>
        {tab === "Dashboard" && <Dashboard data={dashboard} openRepair={openRepair} />}
        {tab === "Customers" && (
          <Customers customers={customers} refresh={refresh} />
        )}
        {tab === "Devices" && (
          <Devices
            devices={devices}
            customers={customers}
            deviceTypes={deviceTypes}
            refresh={refresh}
          />
        )}
        {tab === "Repairs" && (
          <Repairs
            repairs={repairs}
            devices={devices}
            refresh={refresh}
            openRepair={openRepair}
          />
        )}
        {tab === "Parts" && <Parts parts={parts} refresh={refresh} />}
        {tab === "Technicians" && <Technicians technicians={technicians} />}
        {tab === "Repair Detail" && (
          <RepairDetail
            data={selectedRepair}
            technicians={technicians}
            parts={parts}
            refresh={async () => {
              await refresh();
              if (selectedRepair) {
                setSelectedRepair(await api(`/repairs/${selectedRepair.repair.repair_id}`));
              }
            }}
          />
        )}
      </main>
    </div>
  );
}

function Dashboard({ data, openRepair }) {
  if (!data) return <p>Loading...</p>;
  const c = data.counts;
  const s = data.completed_cost_stats || {};
  return (
    <>
      <h2>Dashboard</h2>
      <div className="cards">
        <Metric label="Customers" value={c.customers} />
        <Metric label="Devices" value={c.devices} />
        <Metric label="Active Repairs" value={c.active_repairs} />
        <Metric label="Waiting for Parts" value={c.waiting_for_parts} />
        <Metric label="Completed" value={c.completed_repairs} />
      </div>

      <section>
        <h3>Recent Repair Jobs</h3>
        <table>
          <thead>
            <tr><th>ID</th><th>Customer</th><th>Device</th><th>Date</th><th>Status</th></tr>
          </thead>
          <tbody>
            {data.recent_repairs.map(r => (
              <tr key={r.repair_id} className="clickable" onClick={() => openRepair(r.repair_id)}>
                <td>#{r.repair_id}</td>
                <td>{r.customer_name}</td>
                <td>{r.device_name}</td>
                <td>{r.date_received}</td>
                <td><span className="pill">{r.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section>
        <h3>Completed Repair Cost Summary</h3>
        <div className="cards">
          <Metric label="Completed Repairs" value={s.completed_count ?? 0} />
          <Metric label="Average Cost" value={`$${s.avg_cost ?? 0}`} />
          <Metric label="Minimum Cost" value={`$${s.min_cost ?? 0}`} />
          <Metric label="Maximum Cost" value={`$${s.max_cost ?? 0}`} />
        </div>
      </section>
    </>
  );
}

function Customers({ customers, refresh }) {
  const [form, setForm] = useState({
    first_name: "", last_name: "", email: "", phone: "", city: "", state: "MO"
  });
  const [history, setHistory] = useState(null);

  async function submit(e) {
    e.preventDefault();
    await api("/customers", {
      method: "POST",
      body: JSON.stringify({
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email || null,
        city: form.city || null,
        state: form.state || null,
        phone_numbers: form.phone ? [form.phone] : []
      })
    });
    setForm({ first_name:"", last_name:"", email:"", phone:"", city:"", state:"MO" });
    refresh();
  }

  return (
    <>
      <h2>Customers</h2>
      <section>
        <h3>Add Customer</h3>
        <form onSubmit={submit} className="form-grid">
          <input required placeholder="First name" value={form.first_name}
            onChange={e => setForm({...form, first_name:e.target.value})} />
          <input required placeholder="Last name" value={form.last_name}
            onChange={e => setForm({...form, last_name:e.target.value})} />
          <input placeholder="Email" value={form.email}
            onChange={e => setForm({...form, email:e.target.value})} />
          <input placeholder="Phone" value={form.phone}
            onChange={e => setForm({...form, phone:e.target.value})} />
          <input placeholder="City" value={form.city}
            onChange={e => setForm({...form, city:e.target.value})} />
          <input placeholder="State" value={form.state}
            onChange={e => setForm({...form, state:e.target.value})} />
          <button>Add Customer</button>
        </form>
      </section>

      <section>
        <table>
          <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>City</th><th></th></tr></thead>
          <tbody>
            {customers.map(c => (
              <tr key={c.customer_id}>
                <td>{c.customer_id}</td>
                <td>{c.first_name} {c.last_name}</td>
                <td>{c.email || "—"}</td>
                <td>{c.city || "—"}</td>
                <td>
                  <button onClick={async () => setHistory(await api(`/customers/${c.customer_id}/history`))}>
                    History
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {history && (
        <section>
          <h3>{history.customer.first_name} {history.customer.last_name} — Repair History</h3>
          <table>
            <thead>
              <tr><th>Device</th><th>Type</th><th>Repair</th><th>Date</th><th>Status</th><th>Problem</th></tr>
            </thead>
            <tbody>
              {history.history.map((h, i) => (
                <tr key={i}>
                  <td>{h.brand} {h.model}</td>
                  <td>{h.type_name}</td>
                  <td>{h.repair_id ? `#${h.repair_id}` : "—"}</td>
                  <td>{h.date_received || "—"}</td>
                  <td>{h.status || "—"}</td>
                  <td>{h.problem_description || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </>
  );
}

function Devices({ devices, customers, deviceTypes, refresh }) {
  const [form, setForm] = useState({
    customer_id:"", device_type_id:"", brand:"", model:"", serial_number:""
  });

  async function submit(e) {
    e.preventDefault();
    await api("/devices", {
      method:"POST",
      body:JSON.stringify({
        ...form,
        customer_id:Number(form.customer_id),
        device_type_id:Number(form.device_type_id),
        serial_number:form.serial_number || null
      })
    });
    setForm({customer_id:"", device_type_id:"", brand:"", model:"", serial_number:""});
    refresh();
  }

  return (
    <>
      <h2>Devices</h2>
      <section>
        <h3>Register Device</h3>
        <form onSubmit={submit} className="form-grid">
          <select required value={form.customer_id} onChange={e => setForm({...form,customer_id:e.target.value})}>
            <option value="">Owner</option>
            {customers.map(c => <option key={c.customer_id} value={c.customer_id}>{c.first_name} {c.last_name}</option>)}
          </select>
          <select required value={form.device_type_id} onChange={e => setForm({...form,device_type_id:e.target.value})}>
            <option value="">Device type</option>
            {deviceTypes.map(t => <option key={t.device_type_id} value={t.device_type_id}>{t.type_name}</option>)}
          </select>
          <input required placeholder="Brand" value={form.brand} onChange={e => setForm({...form,brand:e.target.value})} />
          <input required placeholder="Model" value={form.model} onChange={e => setForm({...form,model:e.target.value})} />
          <input placeholder="Serial number" value={form.serial_number} onChange={e => setForm({...form,serial_number:e.target.value})} />
          <button>Register Device</button>
        </form>
      </section>

      <section>
        <table>
          <thead><tr><th>ID</th><th>Owner</th><th>Type</th><th>Brand</th><th>Model</th><th>Serial</th></tr></thead>
          <tbody>
            {devices.map(d => (
              <tr key={d.device_id}>
                <td>{d.device_id}</td><td>{d.customer_name}</td><td>{d.type_name}</td>
                <td>{d.brand}</td><td>{d.model}</td><td>{d.serial_number || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}

function Repairs({ repairs, devices, refresh, openRepair }) {
  const [form, setForm] = useState({device_id:"", problem_description:"", labor_cost:"0"});

  async function submit(e) {
    e.preventDefault();
    await api("/repairs", {
      method:"POST",
      body:JSON.stringify({
        device_id:Number(form.device_id),
        problem_description:form.problem_description,
        labor_cost:Number(form.labor_cost || 0)
      })
    });
    setForm({device_id:"", problem_description:"", labor_cost:"0"});
    refresh();
  }

  return (
    <>
      <h2>Repair Jobs</h2>
      <section>
        <h3>Create Repair Job</h3>
        <form onSubmit={submit} className="form-grid">
          <select required value={form.device_id} onChange={e => setForm({...form,device_id:e.target.value})}>
            <option value="">Device</option>
            {devices.map(d => (
              <option key={d.device_id} value={d.device_id}>
                {d.customer_name} — {d.brand} {d.model}
              </option>
            ))}
          </select>
          <input required placeholder="Problem description" value={form.problem_description}
            onChange={e => setForm({...form,problem_description:e.target.value})} />
          <input type="number" min="0" step="0.01" value={form.labor_cost}
            onChange={e => setForm({...form,labor_cost:e.target.value})} />
          <button>Create Repair</button>
        </form>
      </section>

      <section>
        <table>
          <thead><tr><th>ID</th><th>Customer</th><th>Device</th><th>Date</th><th>Status</th><th>Problem</th></tr></thead>
          <tbody>
            {repairs.map(r => (
              <tr key={r.repair_id} className="clickable" onClick={() => openRepair(r.repair_id)}>
                <td>#{r.repair_id}</td><td>{r.customer_name}</td><td>{r.device_name}</td>
                <td>{r.date_received}</td><td><span className="pill">{r.status}</span></td>
                <td>{r.problem_description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}

function RepairDetail({ data, technicians, parts, refresh }) {
  const [status, setStatus] = useState("");
  const [tech, setTech] = useState("");
  const [hours, setHours] = useState("0");
  const [part, setPart] = useState("");
  const [qty, setQty] = useState("1");
  const [diagTech, setDiagTech] = useState("");
  const [diagDesc, setDiagDesc] = useState("");
  const [diagResult, setDiagResult] = useState("");

  useEffect(() => {
    if (data) setStatus(data.repair.status);
  }, [data]);

  if (!data) return <p>Select a repair first.</p>;
  const id = data.repair.repair_id;

  return (
    <>
      <h2>Repair #{id}</h2>
      <section>
        <div className="detail-grid">
          <div><b>Customer</b><br />{data.repair.customer_name}</div>
          <div><b>Device</b><br />{data.repair.brand} {data.repair.model}</div>
          <div><b>Problem</b><br />{data.repair.problem_description}</div>
          <div><b>Labor</b><br />${Number(data.repair.labor_cost).toFixed(2)}</div>
          <div><b>Parts</b><br />${Number(data.parts_total).toFixed(2)}</div>
          <div><b>Total</b><br /><span className="metric">${Number(data.total_cost).toFixed(2)}</span></div>
        </div>
        <div className="inline">
          <select value={status} onChange={e => setStatus(e.target.value)}>
            {statuses.map(s => <option key={s}>{s}</option>)}
          </select>
          <button onClick={async () => {
            await api(`/repairs/${id}/status`, {
              method:"PATCH",
              body:JSON.stringify({status})
            });
            refresh();
          }}>Update Status</button>
        </div>
      </section>

      <section>
        <h3>Assigned Technicians</h3>
        <table>
          <thead><tr><th>Technician</th><th>Hours</th></tr></thead>
          <tbody>
            {data.technicians.map(t => (
              <tr key={t.technician_id}><td>{t.technician_name}</td><td>{t.hours_worked}</td></tr>
            ))}
          </tbody>
        </table>
        <div className="inline">
          <select value={tech} onChange={e => setTech(e.target.value)}>
            <option value="">Technician</option>
            {technicians.map(t => (
              <option key={t.technician_id} value={t.technician_id}>{t.first_name} {t.last_name}</option>
            ))}
          </select>
          <input type="number" min="0" step="0.25" value={hours} onChange={e => setHours(e.target.value)} />
          <button onClick={async () => {
            await api(`/repairs/${id}/technicians`, {
              method:"POST",
              body:JSON.stringify({technician_id:Number(tech), hours_worked:Number(hours)})
            });
            refresh();
          }}>Assign / Update</button>
        </div>
      </section>

      <section>
        <h3>Diagnostic Steps</h3>
        <table>
          <thead><tr><th>#</th><th>Technician</th><th>Description</th><th>Result</th><th>Date</th></tr></thead>
          <tbody>
            {data.diagnostics.map(d => (
              <tr key={d.step_number}>
                <td>{d.step_number}</td><td>{d.technician_name}</td>
                <td>{d.description}</td><td>{d.result || "—"}</td><td>{d.date_performed}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="form-grid">
          <select value={diagTech} onChange={e => setDiagTech(e.target.value)}>
            <option value="">Technician</option>
            {technicians.map(t => (
              <option key={t.technician_id} value={t.technician_id}>{t.first_name} {t.last_name}</option>
            ))}
          </select>
          <input placeholder="Diagnostic step" value={diagDesc} onChange={e => setDiagDesc(e.target.value)} />
          <input placeholder="Result" value={diagResult} onChange={e => setDiagResult(e.target.value)} />
          <button onClick={async () => {
            await api(`/repairs/${id}/diagnostics`, {
              method:"POST",
              body:JSON.stringify({
                technician_id:Number(diagTech),
                description:diagDesc,
                result:diagResult || null
              })
            });
            setDiagDesc("");
            setDiagResult("");
            refresh();
          }}>Add Step</button>
        </div>
      </section>

      <section>
        <h3>Parts Used</h3>
        <table>
          <thead><tr><th>Part</th><th>Qty</th><th>Price</th><th>Line Total</th></tr></thead>
          <tbody>
            {data.parts.map(p => (
              <tr key={p.part_id}>
                <td>{p.part_name}</td><td>{p.quantity_used}</td>
                <td>${Number(p.price_at_time_of_repair).toFixed(2)}</td>
                <td>${Number(p.line_total).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="inline">
          <select value={part} onChange={e => setPart(e.target.value)}>
            <option value="">Part</option>
            {parts.map(p => (
              <option key={p.part_id} value={p.part_id}>
                {p.part_name} ({p.quantity_in_stock} in stock)
              </option>
            ))}
          </select>
          <input type="number" min="1" value={qty} onChange={e => setQty(e.target.value)} />
          <button onClick={async () => {
            await api(`/repairs/${id}/parts`, {
              method:"POST",
              body:JSON.stringify({part_id:Number(part), quantity_used:Number(qty)})
            });
            refresh();
          }}>Add Part</button>
        </div>
      </section>
    </>
  );
}


function Parts({ parts, refresh }) {
  const [form, setForm] = useState({
    part_name: "", description: "", unit_cost: "", quantity_in_stock: ""
  });

  async function submit(e) {
    e.preventDefault();
    await api("/parts", {
      method: "POST",
      body: JSON.stringify({
        part_name: form.part_name,
        description: form.description || null,
        unit_cost: Number(form.unit_cost),
        quantity_in_stock: Number(form.quantity_in_stock)
      })
    });
    setForm({part_name:"", description:"", unit_cost:"", quantity_in_stock:""});
    refresh();
  }

  async function remove(id) {
    if (!confirm("Delete this part? Parts already used in repair history cannot be deleted.")) return;
    try {
      await api(`/parts/${id}`, {method:"DELETE"});
      refresh();
    } catch (e) {
      alert(e.message);
    }
  }

  return (
    <>
      <h2>Parts Inventory</h2>
      <section>
        <h3>Add Part</h3>
        <form onSubmit={submit} className="form-grid">
          <input required placeholder="Part name" value={form.part_name}
            onChange={e => setForm({...form, part_name:e.target.value})} />
          <input placeholder="Description" value={form.description}
            onChange={e => setForm({...form, description:e.target.value})} />
          <input required type="number" min="0" step="0.01" placeholder="Unit cost"
            value={form.unit_cost}
            onChange={e => setForm({...form, unit_cost:e.target.value})} />
          <input required type="number" min="0" step="1" placeholder="Quantity in stock"
            value={form.quantity_in_stock}
            onChange={e => setForm({...form, quantity_in_stock:e.target.value})} />
          <button>Add Part</button>
        </form>
      </section>

      <section>
        <table>
          <thead><tr><th>ID</th><th>Part</th><th>Description</th><th>Unit Cost</th><th>In Stock</th><th></th></tr></thead>
          <tbody>
            {parts.map(p => (
              <tr key={p.part_id}>
                <td>{p.part_id}</td><td>{p.part_name}</td><td>{p.description || "—"}</td>
                <td>${Number(p.unit_cost).toFixed(2)}</td><td>{p.quantity_in_stock}</td>
                <td><button onClick={() => remove(p.part_id)}>Delete</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}

function Technicians({ technicians }) {
  return (
    <>
      <h2>Technicians</h2>
      <section>
        <table>
          <thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Specialty</th></tr></thead>
          <tbody>
            {technicians.map(t => (
              <tr key={t.technician_id}>
                <td>{t.technician_id}</td>
                <td>{t.first_name} {t.last_name}</td>
                <td>{t.email}</td>
                <td>{t.specialty || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </>
  );
}
