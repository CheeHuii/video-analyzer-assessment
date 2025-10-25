
type Props = {
  convId: string;
  setConvId: (id: string) => void;
};

export default function HistoryPanel({ convId, setConvId }: Props) {
  // For demo we keep simple static convs; ideally fetch a list from backend
  const convs = [{ id: "default", title: "Main" }];

  return (
    <div>
      {convs.map(c => (
        <div key={c.id} className={`p-2 rounded cursor-pointer ${c.id === convId ? 'bg-gray-100' : ''}`} onClick={()=>setConvId(c.id)}>
          {c.title}
        </div>
      ))}
    </div>
  );
}
