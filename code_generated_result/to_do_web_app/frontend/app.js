document.addEventListener('DOMContentLoaded', () => {
    const taskList = document.getElementById('taskList');
    const newTaskInput = document.getElementById('newTask');
    const addTaskButton = document.getElementById('addTask');

    // Function to fetch tasks from the API
    const fetchTasks = async () => {
        try {
            const response = await fetch('/tasks');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const tasks = await response.json();
            displayTasks(tasks);
        } catch (error) {
            console.error('Failed to fetch tasks:', error);
            taskList.innerHTML = `<li class="error">Failed to load tasks. Please try again later.</li>`;
        }
    };

    // Function to display tasks in the UI
    const displayTasks = (tasks) => {
        taskList.innerHTML = ''; // Clear existing list
        tasks.forEach(task => {
            const listItem = document.createElement('li');
            listItem.innerHTML = `
                <input type="checkbox" ${task.is_complete ? 'checked' : ''} data-id="${task.id}">
                <span>${task.description}</span>
                <button class="delete" data-id="${task.id}">Delete</button>
            `;
            taskList.appendChild(listItem);
        });
    };

    // Function to add a new task
    const addTask = async () => {
        const description = newTaskInput.value.trim();
        if (!description) {
            alert('Task description cannot be empty.');
            return;
        }

        try {
            const response = await fetch('/tasks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ description: description }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const newTask = await response.json();
            newTaskInput.value = ''; // Clear input
            fetchTasks(); // Refresh task list
        } catch (error) {
            console.error('Failed to add task:', error);
            alert('Failed to add task. Please try again.');
        }
    };

    // Function to delete a task
    const deleteTask = async (taskId) => {
        try {
            const response = await fetch(`/tasks/${taskId}`, {
                method: 'DELETE',
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            fetchTasks(); // Refresh task list
        } catch (error) {
            console.error('Failed to delete task:', error);
            alert('Failed to delete task. Please try again.');
        }
    };

    // Function to toggle task completion status
    const toggleComplete = async (taskId, isComplete) => {
        try {
            const response = await fetch(`/tasks/${taskId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ is_complete: isComplete }),
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            fetchTasks(); // Refresh task list
        } catch (error) {
            console.error('Failed to update task:', error);
            alert('Failed to update task. Please try again.');
        }
    };

    // Event listeners
    addTaskButton.addEventListener('click', addTask);

    taskList.addEventListener('click', (event) => {
        if (event.target.classList.contains('delete')) {
            const taskId = event.target.dataset.id;
            deleteTask(taskId);
        }

        if (event.target.type === 'checkbox') {
            const taskId = event.target.dataset.id;
            const isComplete = event.target.checked;
            toggleComplete(taskId, isComplete);
        }
    });

    // Initial task load
    fetchTasks();
});