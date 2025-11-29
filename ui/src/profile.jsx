import React, { useEffect, useState } from "react";
import ManageGroupModal from "./components/ManageGroupModal";

export default function Profile({ userId, fetchWithAuth, onClose }) {
  const [user, setUser] = useState(null);
  const [adminGroups, setAdminGroups] = useState([]);
  const [joinedGroups, setJoinedGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editMode, setEditMode] = useState(false);
  const [managedGroup, setManagedGroup] = useState(null);

  const [form, setForm] = useState({
    name: "",
    email: "",
    birthday: "",
    faculty: "",
  });

  const fetchGroups = async () => {
    try {
      const resGroup = await fetchWithAuth(`http://localhost:5000/api/groups/user/${userId}`);
      const dataGroup = await resGroup.json();
      if (!resGroup.ok) throw new Error(dataGroup.error || "Failed to load groups");

      setAdminGroups(dataGroup.filter((g) => g.role === "admin"));
      setJoinedGroups(dataGroup.filter((g) => g.role !== "admin"));
    } catch (err) {
      console.error(err);
      alert("Error loading groups: " + err.message);
    }
  };

  useEffect(() => {
    async function fetchUserData() {
      try {
        const resUser = await fetchWithAuth(`http://localhost:5000/api/users/${userId}`);
        const dataUser = await resUser.json();
        if (!resUser.ok) throw new Error(dataUser.error || "Failed to load user");

        setUser(dataUser);
        setForm({
          name: dataUser.username || "",
          email: dataUser.email || "",
          birthday: dataUser.birthday || "",
          faculty: dataUser.faculty || "",
        });

        await fetchGroups();
      } catch (err) {
        console.error(err);
        alert("Error loading profile: " + err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchUserData();
  }, [userId, fetchWithAuth]);

  const handleSave = async () => {
    try {
      const payload = {
        username: form.name,
        email: form.email,
        birthday: form.birthday || null,
        faculty: form.faculty,
      };

      const res = await fetchWithAuth(`http://localhost:5000/api/users/${userId}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to update profile");

      setUser(data);
      setEditMode(false);
      alert("Profile updated successfully!");
    } catch (err) {
      console.error(err);
      alert("Failed to update profile: " + err.message);
    }
  };

  const handleLeaveGroup = async (groupId) => {
    try {
      const res = await fetchWithAuth(`http://localhost:5000/api/groups/${groupId}/leave`, {
        method: "POST",
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to leave group");

      alert(data.message);
      await fetchGroups(); // Refresh groups
      setManagedGroup(null);
    } catch (err) {
      console.error(err);
      alert("Failed to leave group: " + err.message);
    }
  };

  if (loading) return <div>Loading profile...</div>;
  if (!user) return <div>Unable to load profile.</div>;

  return (
    <div className="card flex flex-col items-center p-4">
      <h2 className="text-xl font-semibold mb-4 text-center">Profile</h2>

      {/* FORM FIELDS */}
      <div className="w-full mb-6 text-center">
        <label className="form-label">Name</label>
        {editMode ? (
          <input
            className="form-input"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
        ) : (
          <p className="py-1">{user.username}</p>
        )}

        <label className="form-label">Email</label>
        {editMode ? (
          <input
            className="form-input"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
        ) : (
          <p className="py-1">{user.email}</p>
        )}

        <label className="form-label">Birthday</label>
        {editMode ? (
          <input
            type="date"
            className="form-input"
            value={form.birthday || ""}
            onChange={(e) => setForm({ ...form, birthday: e.target.value })}
          />
        ) : (
          <p className="py-1">{user.birthday || "—"}</p>
        )}

        <label className="form-label">Faculty</label>
        {editMode ? (
          <input
            className="form-input"
            value={form.faculty}
            onChange={(e) => setForm({ ...form, faculty: e.target.value })}
          />
        ) : (
          <p className="py-1">{user.faculty || "—"}</p>
        )}
      </div>

      {/* ADMIN GROUPS */}
      <div className="mb-6 w-full">
        <h3 className="text-lg font-semibold mb-2">Your Groups (Admin)</h3>
        {adminGroups.length ? (
          <ul>
            {adminGroups.map((g) => (
              <li key={g.id} className="flex justify-between items-center mb-1">
                <span>{g.name}</span>
                <div className="flex gap-2">
                  <button className="btn-secondary text-sm" onClick={() => setManagedGroup(g)}>
                    Manage
                  </button>
                  <button className="btn-cancel text-sm" onClick={() => handleLeaveGroup(g.id)}>
                    Leave
                  </button>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p>You have not created any groups yet.</p>
        )}
      </div>

      {/* JOINED GROUPS */}
      <div className="mb-6 w-full">
        <h3 className="text-lg font-semibold mb-2">Joined Groups</h3>
        {joinedGroups.length ? (
          <ul>
            {joinedGroups.map((g) => (
              <li key={g.id} className="flex justify-between items-center mb-1">
                <span>{g.name}</span>
                <button className="btn-cancel text-sm" onClick={() => handleLeaveGroup(g.id)}>
                  Leave
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p>You have not joined any groups yet.</p>
        )}
      </div>

      {/* BUTTONS */}
      <div className="flex gap-2 mt-4">
        {editMode ? (
          <>
            <button className="btn-primary" onClick={handleSave}>Save</button>
            <button className="btn-cancel" onClick={() => setEditMode(false)}>Cancel</button>
          </>
        ) : (
          <button className="btn-primary" onClick={() => setEditMode(true)}>Edit Profile</button>
        )}
        <button className="btn-cancel" onClick={onClose}>Close</button>
      </div>

      {/* MANAGE GROUP MODAL */}
      {managedGroup && (
        <ManageGroupModal
          group={managedGroup}
          fetchWithAuth={fetchWithAuth}
          onClose={() => setManagedGroup(null)}
        />
      )}
    </div>
  );
}
