import React, { useState, useEffect } from "react";

export default function CreateTask({ userId, onCancel, onAddTask }) {
  const [title, setTitle] = useState("");
  const [deadline, setDeadline] = useState("");
  const [kind, setKind] = useState("");
  const [priority, setPriority] = useState("");
  const [taskType, setTaskType] = useState("my"); // 'my' or 'group'
  const [selectedGroup, setSelectedGroup] = useState("");
  const [assignee, setAssignee] = useState("");
  const [notes, setNotes] = useState("");
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(false);

  // =============================
  // Helper: Authenticated fetch
  // =============================
  async function fetchWithToken(url, options = {}) {
    const token = localStorage.getItem("access_token");
    const refreshToken = localStorage.getItem("refresh_token");

    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...(options.headers || {}),
      },
    });

    if (res.status !== 401) return res;

    if (!refreshToken) throw new Error("Session expired. Please log in again.");

    const refreshRes = await fetch("http://localhost:5000/api/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    const data = await refreshRes.json();
    if (!refreshRes.ok) throw new Error(data.error || "Failed to refresh token");

    localStorage.setItem("access_token", data.access_token);
    if (data.refresh_token) localStorage.setItem("refresh_token", data.refresh_token);

    return await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${data.access_token}`,
        ...(options.headers || {}),
      },
    });
  }

  // =============================
  // Fetch user's groups
  // =============================
  useEffect(() => {
    async function fetchGroups() {
      try {
        const res = await fetchWithToken(`http://localhost:5000/api/groups/user/${userId}`);
        const data = await res.json();
        if (res.ok) {
          // Only include groups where user has a role
          setGroups(data.filter(g => g.role));
        } else {
          console.warn("Failed to load groups:", data.error);
        }
      } catch (err) {
        console.error("Failed to fetch groups:", err);
      }
    }
    if (userId) fetchGroups();
  }, [userId]);

  // =============================
  // Handle Create Task
  // =============================
  const handleSubmit = async (e) => {
    e.preventDefault();

    const task = {
      title,
      deadline,
      kind,
      priority,
      task_type: taskType,
      group: taskType === "group" ? selectedGroup : null,
      assignee: assignee || null,
      notes: notes || null,
      status: "todo",
      user_id: userId,
    };

    setLoading(true);
    try {
      const res = await fetchWithToken("http://localhost:5000/api/tasks", {
        method: "POST",
        body: JSON.stringify(task),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to create task");

      if (onAddTask) onAddTask({ ...task, id: data.task.id });

      // Reset form
      setTitle("");
      setDeadline("");
      setKind("");
      setPriority("");
      setTaskType("my");
      setSelectedGroup("");
      setAssignee("");
      setNotes("");

      onCancel();
    } catch (err) {
      console.error("Error creating task:", err);
      alert("Error creating task: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const isValid =
    title.trim() &&
    deadline &&
    kind &&
    priority &&
    (taskType === "my" || (taskType === "group" && selectedGroup));

  // =============================
  // Render
  // =============================
  return (
    <div className="card">
      <h2 className="text-xl font-semibold mb-4 text-center">Create New Task</h2>

      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <label className="block mb-1 font-medium">
            Title <span style={{ color: "red" }}>*</span>
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            className="w-full p-2 border rounded-md"
          />
        </div>

        <div>
          <label className="block mb-1 font-medium">
            Deadline <span style={{ color: "red" }}>*</span>
          </label>
          <input
            type="date"
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
            required
            className="w-full p-2 border rounded-md"
          />
        </div>

        <div>
          <label className="block mb-1 font-medium">
            Kind <span style={{ color: "red" }}>*</span>
          </label>
          <select
            value={kind}
            onChange={(e) => setKind(e.target.value)}
            required
            className="w-full p-2 border rounded-md"
          >
            <option value="">Select kind</option>
            <option value="homework">Homework Assignment</option>
            <option value="exam">Exam Preparation</option>
            <option value="project">Project Milestone</option>
          </select>
        </div>

        <div>
          <label className="block mb-1 font-medium">
            Priority <span style={{ color: "red" }}>*</span>
          </label>
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value)}
            required
            className="w-full p-2 border rounded-md"
          >
            <option value="">Select priority</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>

        {/* Task Type Toggle */}
        <div className={`toggle-switch ${taskType === "group" ? "group-active" : ""}`}>
          <div className="switch-slider"></div>
          <div
            className={`switch-option ${taskType === "my" ? "active" : ""}`}
            onClick={() => setTaskType("my")}
          >
            My Task
          </div>
          <div
            className={`switch-option ${taskType === "group" ? "active" : ""}`}
            onClick={() => setTaskType("group")}
          >
            Group Task
          </div>
        </div>

        {/* Group Dropdown */}
        {taskType === "group" && (
          <div>
            <label className="block mb-1 font-medium">
              Select Group <span style={{ color: "red" }}>*</span>
            </label>
            <select
              value={selectedGroup}
              onChange={(e) => setSelectedGroup(e.target.value)}
              required
              className="w-full p-2 border rounded-md"
            >
              <option value="">-- Choose a Group --</option>
              {groups.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {/* Optional */}
        <div>
          <label className="block mb-1 font-medium">Assignee</label>
          <input
            type="text"
            value={assignee}
            onChange={(e) => setAssignee(e.target.value)}
            className="w-full p-2 border rounded-md"
          />
        </div>

        <div>
          <label className="block mb-1 font-medium">Notes</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full p-2 border rounded-md"
          />
        </div>

        {/* Buttons */}
        <div className="form-buttons mt-4 flex gap-2">
          <button type="submit" className="btn-primary flex-1" disabled={!isValid || loading}>
            {loading ? "Creating..." : "Create Task"}
          </button>
          <button type="button" onClick={onCancel} className="btn-cancel flex-1" disabled={loading}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}