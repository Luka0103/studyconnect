import React, { useEffect, useState } from "react";

export default function ManageGroupModal({ group, fetchWithAuth, onClose }) {
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchMembers() {
      try {
        setLoading(true);
        const res = await fetchWithAuth(
          `http://localhost:5000/api/groups/${group.id}/members`
        );
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || "Failed to load members");

        setMembers(data.members || []);
      } catch (err) {
        console.error(err);
        alert("Error loading group members: " + err.message);
      } finally {
        setLoading(false);
      }
    }

    if (group) fetchMembers();
  }, [group, fetchWithAuth]);

  const handleKick = async (memberId) => {
    if (!window.confirm("Are you sure you want to remove this user?")) return;

    try {
      const res = await fetchWithAuth(
        `http://localhost:5000/api/groups/${group.id}/kick`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: memberId }),
        }
      );

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to remove user");

      // Remove user from local state to update UI
      setMembers((prev) => prev.filter((m) => m.id !== memberId));
      alert("User removed successfully!");
    } catch (err) {
      console.error(err);
      alert("Error removing user: " + err.message);
    }
  };

  const handlePromote = async (memberId) => {
    if (!window.confirm("Promote this user to admin?")) return;

    try {
      const res = await fetchWithAuth(
        `http://localhost:5000/api/groups/${group.id}/add-admin`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ user_id: memberId }),
        }
      );

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to promote user");

      // Update the role locally
      setMembers((prev) =>
        prev.map((m) =>
          m.id === memberId ? { ...m, role: "admin" } : m
        )
      );
      alert("User promoted to admin!");
    } catch (err) {
      console.error(err);
      alert("Error promoting user: " + err.message);
    }
  };

  if (!group) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content max-w-md w-full p-4">
        <h2 className="text-xl font-semibold mb-4 text-center">
          Manage Group: {group.name}
        </h2>

        {loading ? (
          <p>Loading members...</p>
        ) : members.length ? (
          <ul className="space-y-2">
            {members.map((m) => (
              <li key={m.id} className="flex justify-between items-center">
                <span>
                  {m.username || m.id} {m.role === "admin" && "(Admin)"}
                </span>
                <div className="flex gap-2">
                  {m.role !== "admin" && (
                    <>
                      <button
                        className="btn-cancel text-sm"
                        onClick={() => handleKick(m.id)}
                      >
                        Kick
                      </button>
                      <button
                        className="btn-primary text-sm"
                        onClick={() => handlePromote(m.id)}
                      >
                        Promote
                      </button>
                    </>
                  )}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p>No members in this group.</p>
        )}

        <div className="flex justify-end mt-4">
          <button className="btn-cancel" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
