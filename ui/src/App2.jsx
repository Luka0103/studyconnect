import React, { useState, useEffect, useMemo, useCallback } from "react";
import { DragDropContext, Droppable } from "react-beautiful-dnd";
import TaskCard from "./components/TaskCard.jsx";
import EditTaskModal from "./components/Task.jsx";
import CreateTask from "./create/create_task.jsx";
import CreateGroup from "./create/create_group.jsx";
import JoinGroup from "./create/join_group.jsx";
import Profile from "./profile.jsx";
import { fetchWithToken } from "./api.js";

export default function App2({ token, userId, onLogout }) {
  const columnNames = {
    todo: "To Do",
    inProgress: "In Progress",
    done: "Done",
    expired: "Expired",
  };
  const columnKeys = useMemo(() => ["todo", "inProgress", "done", "expired"], []);

  const [columns, setColumns] = useState({
    todo: [],
    inProgress: [],
    done: [],
    expired: [],
  });
  const [selectedTask, setSelectedTask] = useState(null);
  const [showForm, setShowForm] = useState(null);
  const [showProfile, setShowProfile] = useState(false);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentToken, setCurrentToken] = useState(token);

  // =============================
  // API Calls
  // =============================

  const fetchTasks = useCallback(async () => {
    if (!userId) return;
    try {
      // Use the imported fetchWithToken which already returns JSON
      const data = await fetchWithToken(`http://localhost:5000/api/tasks`);

      const newCols = { todo: [], inProgress: [], done: [], expired: [] };
      data.forEach((task) => {
        // Normalize status from backend (e.g., 'in_progress' to 'inProgress')
        let statusKey = task.status.replace(/_([a-z])/g, (g) => g[1].toUpperCase());
        if (!newCols[statusKey]) {
          statusKey = 'todo'; // Fallback to 'todo' if status is invalid
        }
        newCols[statusKey].push({ ...task, id: String(task.id) });
      });
      setColumns(newCols);
    } catch (err) {
      console.error("Failed to fetch tasks:", err);
      setColumns({ todo: [], inProgress: [], done: [], expired: [] });
    }
  }, [userId]);

  const fetchGroups = useCallback(async () => {
    if (!userId) return;
    try {
      const data = await fetchWithToken(`http://localhost:5000/api/groups/user/${userId}`);
      setGroups(data);
    } catch (err) {
      console.error("Failed to fetch groups:", err);
    }
  }, [userId]);

  const handleAddTask = async (newTask) => {
    try {
      const data = await fetchWithToken(`http://localhost:5000/api/tasks`, {
        method: "POST",
        body: JSON.stringify(newTask),
      });

      const task = { ...data.task, id: String(data.task.id) };
      const statusKey = (task.status || "todo").replace(/_([a-z])/g, (g) => g[1].toUpperCase());

      setColumns((prev) => ({
        ...prev,
        [statusKey]: [...(prev[statusKey] || []), task],
      }));
      setShowForm(null);
    } catch (err) {
      alert("Error creating task: " + err.message);
    }
  };

  const handleUpdateTask = async (updatedTask) => {
    try {
      const data = await fetchWithToken(
        `http://localhost:5000/api/tasks/${updatedTask.id}`,
        {
          method: "PUT",
          body: JSON.stringify(updatedTask),
        }
      );

      const task = { ...data.task, id: String(data.task.id) };
      const statusKey = (task.status || "todo").replace(/_([a-z])/g, (g) => g[1].toUpperCase());

      setColumns((prev) => {
        const newCols = { ...prev };
        Object.keys(newCols).forEach((col) => {
          newCols[col] = newCols[col].filter((t) => t.id !== task.id);
        });
        newCols[statusKey].push(task);
        return newCols;
      });
      setSelectedTask(null);
    } catch (err) {
      alert("Error updating task: " + err.message);
    }
  };

  const handleJoinGroup = async (groupId) => {
    try {
      await fetchWithToken(`http://localhost:5000/api/groups/join`, {
        method: "POST",
        body: JSON.stringify({ user_id: userId, group_id: groupId }),
      });

      fetchGroups();
      fetchTasks(); 
      setShowForm(null);
    } catch (err) {
      alert("Error joining group: " + err.message);
    }
  };

  // =============================
  // Drag & Drop
  // =============================

  const onDragEnd = async (result) => {
    const { source, destination, draggableId } = result;
    if (!destination) return;
    if (
      source.droppableId === destination.droppableId &&
      source.index === destination.index
    )
      return;

    const column = Array.from(columns[source.droppableId]);

    if (source.droppableId === destination.droppableId) {
      // Moving within same column
      const [movedTask] = column.splice(source.index, 1);
      column.splice(destination.index, 0, movedTask);
      setColumns((prev) => ({
        ...prev,
        [source.droppableId]: column,
      }));
    } else {
      // Moving to a different column
      const sourceTasks = Array.from(columns[source.droppableId]);
      const destTasks = Array.from(columns[destination.droppableId]);
      const [movedTask] = sourceTasks.splice(source.index, 1);
      movedTask.status = destination.droppableId;
      destTasks.splice(destination.index, 0, movedTask);

      setColumns((prev) => ({
        ...prev,
        [source.droppableId]: sourceTasks,
        [destination.droppableId]: destTasks,
      }));
    }

    // Update backend
    try {
      await fetchWithToken(`http://localhost:5000/api/tasks/${draggableId}`, {
        method: "PUT",
        body: JSON.stringify({ status: destination.droppableId }),
      });
    } catch (err) {
      console.error("Failed to update task:", err);
      fetchTasks();
    }
  };

  // =============================
  // Initial Data Load & Refresh Loop
  // =============================

  useEffect(() => {
    if (userId) {
      fetchTasks();
      fetchGroups();
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    const interval = setInterval(async () => {
      const refreshToken = localStorage.getItem("refresh_token");
      if (!refreshToken) return;
      try {
        const res = await fetch("http://localhost:5000/api/refresh", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        const data = await res.json();
        if (res.ok && data.access_token) {
          localStorage.setItem("access_token", data.access_token);
          if (data.refresh_token) {
            localStorage.setItem("refresh_token", data.refresh_token);
          }
          setCurrentToken(data.access_token);
        }
      } catch (err) {
        console.warn("Auto-refresh failed:", err);
      }
    }, 240000);
    return () => clearInterval(interval);
  }, []);

  // =============================
  // Render
  // =============================

  if (loading) return <div>Loading...</div>;

  return (
    <div className="app-container">
      <div className="top-right-buttons">
        <button className="btn-primary" onClick={() => setShowProfile(true)}>
          Profile
        </button>
        <button className="btn-cancel" onClick={onLogout}>
          Logout
        </button>
      </div>

      <h1 className="title-with-icon">
        <img
          src="/assets/StudyConnectLogo.png"
          alt="logo"
          className="title-icon"
        />
        StudyConnect
      </h1>

      <DragDropContext onDragEnd={onDragEnd}>
        <div className="kanban-board">
          {columnKeys.map((colId) => (
            <Droppable droppableId={colId} key={colId}>
              {(provided) => (
                <div
                  className="kanban-column"
                  ref={provided.innerRef}
                  {...provided.droppableProps}
                >
                  <h3 className="kanban-column-header">{columnNames[colId]}</h3>
                  <div
                    className="kanban-column-tasks"
                    style={{ transition: "all 0.2s ease" }}
                  >
                    {columns[colId].map((task, index) => (
                      <TaskCard
                        key={task.id}
                        task={task}
                        index={index}
                        onClick={setSelectedTask}
                      />
                    ))}
                    {provided.placeholder}
                  </div>
                </div>
              )}
            </Droppable>
          ))}
        </div>
      </DragDropContext>

      <div className="button-container">
        <button
          className="btn-primary"
          onClick={() => setShowForm("task")}
        >
          Create Task
        </button>
        <button
          className="btn-primary"
          onClick={() => setShowForm("join")}
        >
          Join a Group
        </button>
        <button
          className="btn-primary"
          onClick={() => setShowForm("group")}
        >
          Create a Group
        </button>
      </div>

      {showForm && (
        <div className="modal-overlay">
          <div className="modal-content">
            {showForm === "task" && (
              <CreateTask
                userId={userId}
                onCancel={() => setShowForm(null)}
                onAddTask={handleAddTask}
              />
            )}
            {showForm === "group" && (
              <CreateGroup onCancel={() => setShowForm(null)} />
            )}
            {showForm === "join" && (
              <JoinGroup
                userId={userId}
                groups={groups}
                onCancel={() => setShowForm(null)}
                onJoinGroup={handleJoinGroup}
              />
            )}
          </div>
        </div>
      )}

      {showProfile && (
        <div className="modal-overlay">
          <div className="modal-content">
            <Profile
              userId={userId}
              onUpdate={fetchTasks} // Pass the fetchTasks function
              onClose={() => setShowProfile(false)}
            />
          </div>
        </div>
      )}

    {selectedTask && (
      <EditTaskModal
        task={selectedTask}
        userId={userId}
        onUpdate={fetchTasks} 
        onSave={handleUpdateTask}
        onCancel={() => setSelectedTask(null)}
      />
    )}
    </div>
  );
}
