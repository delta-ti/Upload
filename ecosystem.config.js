// ecosystem.config.js
module.exports = {
  apps: [
    {
      name: "pm2plus-flask",
      script: "app.py",
      interpreter: "./venv/Scripts/python.exe", // Caminho para o Python do venv
      watch: false,
      env: {
        FLASK_ENV: "production",
        PYTHONUNBUFFERED: "1",
        PORT: "5001"
      }
    }
  ]
};
