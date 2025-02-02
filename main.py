from flask import Flask, render_template, request, jsonify
from threading import Thread
import time
from instagrapi import Client

app = Flask(__name__)

client = None
running_tasks = {}

def authenticate(cookie):
    global client
    try:
        client = Client()
        client.set_cookie(cookie)
        client.get_timeline_feed()  # Test authentication
        return True, "Authenticated successfully!"
    except Exception as e:
        return False, str(e)

def send_messages(task_id, target, is_group, delay, messages):
    try:
        for message in messages:
            if not running_tasks.get(task_id):
                break
            message = message.strip()
            if is_group:
                client.direct_send(message, [], thread_id=target)
            else:
                client.direct_send(message, [target])
            time.sleep(delay)
        running_tasks.pop(task_id, None)
    except Exception as e:
        running_tasks.pop(task_id, None)
        print(f"Error in task {task_id}: {str(e)}")

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Instagram Auto Messaging</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                padding: 20px;
                background-color: #f4f4f9;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background: #fff;
                border-radius: 8px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            h1 {
                text-align: center;
                color: #333;
            }
            label {
                font-weight: bold;
                margin-top: 10px;
                display: block;
                color: #555;
            }
            input, select, textarea, button {
                width: 100%;
                padding: 10px;
                margin-top: 5px;
                margin-bottom: 15px;
                border: 1px solid #ccc;
                border-radius: 5px;
            }
            button {
                background-color: #007BFF;
                color: white;
                border: none;
                cursor: pointer;
            }
            button:hover {
                background-color: #0056b3;
            }
            .error {
                color: red;
                font-size: 0.9em;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Instagram Auto Messaging</h1>
            <form id="messagingForm">
                <label for="cookie">Instagram Cookie:</label>
                <input type="text" id="cookie" name="cookie" required>

                <label for="target">Target Group ID or Username:</label>
                <input type="text" id="target" name="target" required>

                <label for="is_group">Is this a group? (Yes/No):</label>
                <select id="is_group" name="is_group">
                    <option value="No">No</option>
                    <option value="Yes">Yes</option>
                </select>

                <label for="delay">Delay (seconds):</label>
                <input type="number" id="delay" name="delay" required>

                <label for="messages">Messages (one per line):</label>
                <textarea id="messages" name="messages" rows="5" required></textarea>

                <button type="button" onclick="startMessaging()">Start Messaging</button>
                <button type="button" onclick="stopMessaging()" style="background-color: red;">Stop Task</button>

                <div id="response" class="error"></div>
            </form>
        </div>

        <script>
            async function startMessaging() {
                const formData = new FormData(document.getElementById('messagingForm'));
                const response = await fetch('/start', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                const responseDiv = document.getElementById('response');
                if (result.success) {
                    responseDiv.style.color = 'green';
                    responseDiv.textContent = `Task started successfully! Task ID: ${result.task_id}`;
                } else {
                    responseDiv.style.color = 'red';
                    responseDiv.textContent = `Error: ${result.error}`;
                }
            }

            async function stopMessaging() {
                const task_id = prompt("Enter the Task ID to stop:");
                if (!task_id) return;

                const formData = new FormData();
                formData.append('task_id', task_id);

                const response = await fetch('/stop', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                const responseDiv = document.getElementById('response');
                if (result.success) {
                    responseDiv.style.color = 'green';
                    responseDiv.textContent = 'Task stopped successfully!';
                } else {
                    responseDiv.style.color = 'red';
                    responseDiv.textContent = `Error: ${result.error}`;
                }
            }
        </script>
    </body>
    </html>
    '''

@app.route('/start', methods=['POST'])
def start_task():
    global client

    data = request.form
    cookie = data.get('cookie')
    target = data.get('target')
    is_group = data.get('is_group') == "Yes"
    delay = data.get('delay')
    messages = data.get('messages', '').split('\n')

    if not (cookie and target and delay and messages):
        return jsonify({"success": False, "error": "All fields are required!"})

    try:
        delay = int(delay)
    except ValueError:
        return jsonify({"success": False, "error": "Delay must be a number!"})

    auth_status, auth_message = authenticate(cookie)
    if not auth_status:
        return jsonify({"success": False, "error": auth_message})

    task_id = str(int(time.time()))
    running_tasks[task_id] = True
    Thread(target=send_messages, args=(task_id, target, is_group, delay, messages), daemon=True).start()

    return jsonify({"success": True, "task_id": task_id})

@app.route('/stop', methods=['POST'])
def stop_task():
    task_id = request.form.get('task_id')
    if not task_id or task_id not in running_tasks:
        return jsonify({"success": False, "error": "Invalid task ID!"})

    running_tasks[task_id] = False
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
