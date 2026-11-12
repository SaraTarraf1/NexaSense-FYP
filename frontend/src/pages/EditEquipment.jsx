import { useParams } from "react-router-dom";
import EquipmentForm from "../components/EquipmentForm";

export default function EditEquipment() {
  const { equipmentId } = useParams();
  return <EquipmentForm key={equipmentId} equipmentId={equipmentId} />;
}
