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
  const [progress, setProgress] = useState(0);
  const [groups, setGroups] = useState([]);

  useEffect(() => {
    // Fetch groups for "group task" selection
    async function fetchGroups() {
      try {
        const res = await fetch(`http://localhost:5000/api/groups/user/admin/${userId}`);
        const data = await res.json();
        if (res.ok) setGroups(data.filter(g => g.role)); // only admin groups
      } catch (err) {
        console.error("Failed to fetch groups:", err);
      }
    }
    if (userId) fetchGroups();
  }, [userId]);

  const handleSubmit = (e) => {
    e.preventDefault();

    const task = {
      title,
      deadline,
      kind,
      priority,
      task_type: taskType,
      group_id: taskType === "group" ? selectedGroup : null,
      assignee: assignee || null,
      notes: notes || null,
      progress,
      status: "todo",
      user_id: userId,
    };

    // Pass task object to parent (App2) without calling API here
    if (onAddTask) onAddTask(task);

    // Reset form
    setTitle(""); setDeadline(""); setKind(""); setPriority("");
    setTaskType("my"); setSelectedGroup(""); setAssignee(""); setNotes(""); setProgress(0);
    onCancel();
  };

  const isValid =
    title.trim() &&
    deadline &&
    kind &&
    priority &&
    (taskType === "my" || (taskType === "group" && selectedGroup));

  return (
    <div className="card">
      <h2 className="text-xl font-semibold mb-4 text-center">Create New Task</h2>
      <form className="space-y-4" onSubmit={handleSubmit}>
        {/* Title */}
        <div>
          <label className="block mb-1 font-medium">Title *</label>
          <input type="text" value={title} onChange={(e) => setTitle(e.target.value)}
                 required className="w-full p-2 border rounded-md"/>
        </div>

        {/* Deadline */}
        <div>
          <label className="block mb-1 font-medium">Deadline *</label>
          <input type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)}
                 required className="w-full p-2 border rounded-md"/>
        </div>

        {/* Kind */}
        <div>
          <label className="block mb-1 font-medium">Kind *</label>
          <select value={kind} onChange={(e) => setKind(e.target.value)} required className="w-full p-2 border rounded-md">
            <option value="">Select kind</option>
            <option value="homework">Homework Assignment</option>
            <option value="exam">Exam Preparation</option>
            <option value="project">Project Milestone</option>
          </select>
        </div>

        {/* Priority */}
        <div>
          <label className="block mb-1 font-medium">Priority *</label>
          <select value={priority} onChange={(e) => setPriority(e.target.value)} required className="w-full p-2 border rounded-md">
            <option value="">Select priority</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
          </select>
        </div>

        {/* Task Type Toggle */}
        <div className={`toggle-switch ${taskType === "group" ? "group-active" : ""}`}>
          <div className="switch-slider"></div>
          <div className={`switch-option ${taskType === "my" ? "active" : ""}`} onClick={() => setTaskType("my")}>My Task</div>
          <div className={`switch-option ${taskType === "group" ? "active" : ""}`} onClick={() => setTaskType("group")}>Group Task</div>
        </div>

        {/* Group Selection */}
        {taskType === "group" && (
          <div>
            <label className="block mb-1 font-medium">Select Group *</label>
            <select value={selectedGroup} onChange={(e) => setSelectedGroup(e.target.value)}
                    className="w-full p-2 border rounded-md">
              <option value="">-- Choose a Group --</option>
              {groups.map((group) => (
                <option key={group.id} value={group.id}>{group.name}</option>
              ))}
            </select>
          </div>
        )}

        {/* Optional Fields */}
        <div>
          <label className="block mb-1 font-medium">Assignee</label>
          <input type="text" value={assignee} onChange={(e) => setAssignee(e.target.value)}
                 className="w-full p-2 border rounded-md"/>
        </div>

        <div>
          <label className="block mb-1 font-medium">Notes</label>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)}
                    className="w-full p-2 border rounded-md"/>
        </div>

        <div>
          <label className="block mb-1 font-medium">Progress: {progress}%</label>
          <input type="range" min="0" max="100" value={progress} onChange={(e) => setProgress(Number(e.target.value))}
                 className="w-full"/>
        </div>

        {/* Buttons */}
        <div className="form-buttons mt-4 flex gap-2">
          <button type="submit" className="btn-primary flex-1" disabled={!isValid}>
            Create Task
          </button>
          <button type="button" onClick={onCancel} className="btn-cancel flex-1">Cancel</button>
        </div>
      </form>
    </div>
  );
}
