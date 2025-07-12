import os

# Define the directory structure
structure = {
    "server": {
        "app": {
            "api": [
                "auth.py",
                "questions.py",
                "answers.py",
                "notifications.py"
            ],
            "models": [
                "user.py",
                "question.py",
                "answer.py",
                "notification.py"
            ],
            "utils": [
                "db.py",
                "upload.py"
            ],
            "init.py": "file",
            "config.py": "file"
        },
        "tests": [
            "test_questions.py"
        ],
        "main.py": "file",
        "requirements.txt": "file",
        ".env": "file"
    },
    "database": [
        "schema.sql"
    ]
}
