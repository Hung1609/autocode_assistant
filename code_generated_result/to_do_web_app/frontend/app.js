document.addEventListener('DOMContentLoaded', () => {
  const taskList = document.getElementById('taskList');
  const newTaskInput = document.getElementById('newTask');
  const addTaskButton = document.getElementById('addTask');

  // Function to fetch tasks from the backend API
  async function fetchTasks() {
    try {
      const response = await fetch('/tasks'); // Assuming backend is served on the same origin
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      const tasks = await response.json();
      displayTasks(tasks);
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
      alert('Failed to fetch tasks. See console for details.'); // Basic error handling
    }
  }

  // Function to display tasks in the UI
  function displayTasks(tasks) {
    taskList.innerHTML = ''; // Clear existing list
    tasks.forEach(task => {
      const listItem = document.createElement('li');
      listItem.innerHTML = `
        <input type="checkbox" data-id="${task.id}" ${task.is_complete ? 'checked' : ''}>
        <span>${task.description}</span>
        <button data-id="${task.id}">Delete</button>
      `;
      taskList.appendChild(listItem);
    });
  }

  // Function to add a new task
  async function addTask() {
    const description = newTaskInput.value.trim();
    if (description === '') {
      alert('Task description cannot be empty.');
      return;
    }

    try {
      const response = await fetch('/tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ description: description })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const newTask = await response.json();
      newTaskInput.value = ''; // Clear input
      fetchTasks(); // Refresh task list
    } catch (error) {
      console.error('Failed to add task:', error);
      alert('Failed to add task. See console for details.');
    }
  }

  // Function to delete a task
  async function deleteTask(taskId) {
    try {
      const response = await fetch(`/tasks/${taskId}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      fetchTasks(); // Refresh task list
    } catch (error) {
      console.error('Failed to delete task:', error);
      alert('Failed to delete task. See console for details.');
    }
  }

  // Function to toggle task completion status
  async function toggleComplete(taskId, isComplete) {
    try {
      const response = await fetch(`/tasks/${taskId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ is_complete: isComplete })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      fetchTasks(); // Refresh task list
    } catch (error) {
      console.error('Failed to update task:', error);
      alert('Failed to update task. See console for details.');
    }
  }

  // Event listeners
  addTaskButton.addEventListener('click', addTask);

  taskList.addEventListener('click', (event) => {
    if (event.target.tagName === 'BUTTON') {
      const taskId = event.target.dataset.id;
      deleteTask(taskId);
    } else if (event.target.tagName === 'INPUT' && event.target.type === 'checkbox') {
      const taskId = event.target.dataset.id;
      const isComplete = event.target.checked;
      toggleComplete(taskId, isComplete);
    }
  });

  // Initial task fetch on page load
  fetchTasks();
});