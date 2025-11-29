import React, { useState, useEffect } from "react";
import { fetchWithToken } from '../api.js'; 

export default function EditTaskModal({ task, onSave, onCancel, userId }) {
  const [title, setTitle] = useState("");
  const [deadline, setDeadline] = useState("");
  const [kind, setKind] = useState("");
  const [priority, setPriority] = useState("");
  const [taskType, setTaskType] = useState("my");
  const [selectedGroup, setSelectedGroup] = useState("");
  const [assignee, setAssignee] = useState("");
  const [notes, setNotes] = useState("");
  const [progress, setProgress] = useState(0);
  const [groups, setGroups] = useState([]);


  useEffect(() => {
    async function fetchGroups() {
      try {
        const data = await fetchWithToken(`http://localhost:5000/api/groups/user/${userId}`);
        setGroups(data.filter(g => g.role));
      } catch (err) {
        console.error("Failed to fetch groups:", err);
      }
    }
    if (userId) fetchGroups();
  }, [userId, fetchWithToken]);

  useEffect(() => {
    if (task) {
      setTitle(task.title || "");
      setDeadline(task.deadline || "");
      setKind(task.kind || "");
      setPriority(task.priority || "");
      setTaskType(task.group ? "group" : "my");
      setSelectedGroup(task.group ? task.group.id : "");
      setAssignee(task.assignee || "");
      setNotes(task.notes || "");
      setProgress(task.progress || 0);
    }
  }, [task]);

  const handleSave = () => {
    const updatedTask = {
      ...task,
      title,
      deadline,
      kind,
      priority,
      group_id: taskType === "group" ? selectedGroup : null,
      assignee: assignee || null,
      notes: notes || null,
      progress,
    };
    onSave(updatedTask);
  };

  const isValid =
    title.trim() &&
    deadline &&
    kind &&
    priority &&
    (taskType === "my" || (taskType === "group" && selectedGroup));

  if (!task) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content max-w-md w-full p-4">
        <h2 className="text-xl font-semibold mb-4">Edit Task</h2>
        {/* Title, Deadline, Kind, Priority */}
        <div>
          <label className="block mb-1 font-medium">Title *</label>
          <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} className="w-full p-2 border rounded-md"/>
        </div>

        <div>
          <label className="block mb-1 font-medium">Deadline *</label>
          <input type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} className="w-full p-2 border rounded-md"/>
        </div>

        <div>
          <label className="block mb-1 font-medium">Kind *</label>
          <select value={kind} onChange={(e) => setKind(e.target.value)} className="w-full p-2 border rounded-md">
            <option value="">Select kind</option>
            <option value="homework">Homework Assignment</option>
            <option value="exam">Exam Preparation</option>
            <option value="project">Project Milestone</option>
          </select>
        </div>

        <div>
          <label className="block mb-1 font-medium">Priority *</label>
          <select value={priority} onChange={(e) => setPriority(e.target.value)} className="w-full p-2 border rounded-md">
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
            <select value={selectedGroup} onChange={(e) => setSelectedGroup(e.target.value)} className="w-full p-2 border rounded-md">
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
          <input type="text" value={assignee} onChange={(e) => setAssignee(e.target.value)} className="w-full p-2 border rounded-md"/>
        </div>

        <div>
          <label className="block mb-1 font-medium">Notes</label>
          <textarea value={notes} onChange={(e) => setNotes(e.target.value)} className="w-full p-2 border rounded-md"/>
        </div>

        <div>
          <label className="block mb-1 font-medium">Progress: {progress}%</label>
          <input type="range" min="0" max="100" value={progress} onChange={(e) => setProgress(Number(e.target.value))} className="w-full"/>
        </div>

        {/* Buttons */}
        <div className="flex gap-2 mt-4">
          <button className="btn-primary flex-1" onClick={handleSave} disabled={!isValid}>Save</button>
          <button className="btn-cancel flex-1" onClick={onCancel}>Cancel</button>
        </div>
      </div>
    </div>
  );
}
