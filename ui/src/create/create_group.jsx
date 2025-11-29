import React, { useState } from "react";

export default function CreateGroup({ userId, onCancel, onAddGroup }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [groupNumber, setGroupNumber] = useState(generateGroupNumber());
  const [inviteLink, setInviteLink] = useState(generateInviteLink());
  const [loading, setLoading] = useState(false);

  // -----------------------------
  // Utility Generators
  // -----------------------------
  function generateGroupNumber() {
    return Math.floor(1000 + Math.random() * 9000); // 4-digit number
  }

  function generateInviteLink() {
    const randomString = Math.random().toString(36).substring(2, 8);
    return `https://myapp.com/invite/${randomString}`;
  }

  // -----------------------------
  // Submit new group to backend
  // -----------------------------
  const handleSubmit = async (e) => {
    e.preventDefault();

    const token = localStorage.getItem("access_token");
    if (!token) {
      alert("You must be logged in to create a group.");
      return;
    }

    const group = {
      name,
      description,
      groupNumber,
      inviteLink,
    };

    setLoading(true);

    try {
      // 1️⃣ Create the group
      const res = await fetch("http://localhost:5000/api/groups", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(group),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to create group");

      const groupId = data.group?.id || Date.now();
      console.log("✅ Group created:", data);

      // 3️⃣ Notify parent component
      if (onAddGroup) {
        onAddGroup({ ...group, id: groupId, role: "admin" });
      }

      // 4️⃣ Reset form
      setName("");
      setDescription("");
      setGroupNumber(generateGroupNumber());
      setInviteLink(generateInviteLink());

      onCancel(); // close modal
    } catch (err) {
      console.error("❌ Error creating group:", err);
      alert("Error creating group: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  // -----------------------------
  // Render UI
  // -----------------------------
  return (
    <div className="card">
      <h2 className="text-xl font-semibold mb-4 text-center">Create New Group</h2>

      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <label className="block mb-1 font-medium">
            Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full p-2 border rounded-md"
          />
        </div>

        <div>
          <label className="block mb-1 font-medium">Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="w-full p-2 border rounded-md"
          />
        </div>

        <div>
          <label className="block mb-1 font-medium">Group #</label>
          <input
            type="text"
            value={groupNumber}
            readOnly
            className="w-full p-2 border rounded-md bg-gray-100 text-gray-600"
          />
        </div>

        <div>
          <label className="block mb-1 font-medium">Invite Link</label>
          <input
            type="text"
            value={inviteLink}
            readOnly
            className="w-full p-2 border rounded-md bg-gray-100 text-gray-600"
          />
        </div>

        <div className="form-buttons mt-4 flex gap-2">
          <button
            type="submit"
            className="btn-primary flex-1 bg-blue-600 text-white p-2 rounded hover:bg-blue-700 transition"
            disabled={loading}
          >
            {loading ? "Creating..." : "Create Group"}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="btn-cancel flex-1 bg-gray-300 p-2 rounded hover:bg-gray-400 transition"
            disabled={loading}
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
