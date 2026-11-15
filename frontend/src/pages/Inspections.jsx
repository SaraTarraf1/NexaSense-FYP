
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import EquipmentLayout from "../components/EquipmentLayout.jsx";

import { getAllEquipment } from "../services/equipmentService.js";
import {
  getAllInspections,
  startInspection,
} from "../services/inspectionService.js";

import "./Inspections.css";


export default function Inspections() {
  const navigate = useNavigate();

  const [equipment, setEquipment] = useState([]);
  const [inspections, setInspections] = useState([]);

  const [selectedEquipmentId, setSelectedEquipmentId] = useState("");
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");


  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      try {
        const [equipmentData, inspectionData] =
          await Promise.all([
            getAllEquipment(),
            getAllInspections(),
          ]);

        if (cancelled) return;

        setEquipment(equipmentData);
        setInspections(inspectionData);
      } catch (err) {
        if (!cancelled) {
          setError(err.message);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadData();

    return () => {
      cancelled = true;
    };
  }, []);


  async function handleStartInspection(event) {
    event.preventDefault();

    if (!selectedEquipmentId) {
      setError("Please select equipment first.");
      return;
    }

    setStarting(true);
    setError("");

    try {
      const inspection = await startInspection(
        Number(selectedEquipmentId)
      );

      navigate(`/inspections/${inspection.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setStarting(false);
    }
  }


  const activeEquipment = equipment.filter(
    (item) => item.status === "active"
  );


  return (
    <EquipmentLayout breadcrumb="Inspections">
      <div className="inspections-page">

        <div className="inspections-header">
          <div>
            <p className="inspections-eyebrow">
              NEXASENSE / MONITORING
            </p>

            <h1>Equipment Inspections</h1>

            <p>
              Start an inspection to automatically collect
              sensor measurements from your equipment.
            </p>
          </div>
        </div>


        {error && (
          <div className="inspections-error" role="alert">
            {error}
          </div>
        )}


        <section className="inspections-card">
          <h2>Start New Inspection</h2>

          <p>
            Select active equipment. The required sensors
            will be configured automatically.
          </p>

          {loading ? (
            <p>Loading equipment...</p>
          ) : (
            <form onSubmit={handleStartInspection}>

              <label htmlFor="inspection-equipment">
                Equipment
              </label>

              <select
                id="inspection-equipment"
                value={selectedEquipmentId}
                onChange={(event) =>
                  setSelectedEquipmentId(event.target.value)
                }
                required
              >
                <option value="">
                  Select equipment
                </option>

                {activeEquipment.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name || item.equipment_name ||
                      `Equipment #${item.id}`}
                    {" — "}
                    {item.equipment_type}
                  </option>
                ))}
              </select>

              <button
                type="submit"
                disabled={starting || activeEquipment.length === 0}
              >
                {starting
                  ? "Starting Inspection..."
                  : "Start Inspection"}
              </button>

              {activeEquipment.length === 0 && (
                <p>
                  No active equipment available.{" "}
                  <Link to="/equipment">
                    View Equipment
                  </Link>
                </p>
              )}

            </form>
          )}
        </section>


        <section className="inspections-card">
          <h2>Inspection History</h2>

          {loading ? (
            <p>Loading inspections...</p>
          ) : inspections.length === 0 ? (
            <p>No inspections have been created yet.</p>
          ) : (
            <div className="inspections-table-wrapper">
              <table className="inspections-table">
                <thead>
                  <tr>
                    <th>Inspection</th>
                    <th>Equipment</th>
                    <th>Status</th>
                    <th>Started</th>
                    <th>Action</th>
                  </tr>
                </thead>

                <tbody>
                  {inspections.map((inspection) => (
                    <tr key={inspection.id}>
                      <td>#{inspection.id}</td>

                      <td>
                        {equipment.find(
                          (item) =>
                            item.id === inspection.equipment_id
                        )?.name ||
                          `Equipment #${inspection.equipment_id}`}
                      </td>

                      <td>
                        <span
                          className={`inspection-status ${inspection.status}`}
                        >
                          {inspection.status}
                        </span>
                      </td>

                      <td>
                        {new Date(
                          inspection.started_at
                        ).toLocaleString()}
                      </td>

                      <td>
                        <Link
                          to={`/inspections/${inspection.id}`}
                        >
                          View
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

      </div>
    </EquipmentLayout>
  );
}
