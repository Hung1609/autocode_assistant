from flask import Flask, request, jsonify

app = Flask(__name__)

tasks = []

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    return jsonify(tasks)

@app.route('/api/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    if 'title' not in data:
        return jsonify({'error': 'Title is required'}), 400
    task = {'title': data['title']}
    tasks.append(task)
    return jsonify(task), 201

if __name__ == '__main__':
    app.run(debug=True)