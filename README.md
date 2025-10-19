# Fitness Tracker Flask App

A Flask-based fitness tracker application for managing workouts, food logging, and providing AI-powered fitness recommendations.

---

## Features Implemented

- User registration and login
- Food logging with macros tracking (calories, protein, carbs, fats)
- Workout tracking with exercises, sets, and reps
- User profile and settings for macro goals
- Dashboard showing daily nutrition and workout summaries
- AI Coach integration for personalized guidance
- Admin panel to manage users, food logs, and workouts

---

## Project Structure

fitness_tracker/

├── app.py # Main Flask backend logic

├── requirements.txt # Python dependencies

├── .gitignore # Files/folders to ignore in Git

├── static/ # CSS, JS, images

├── templates/ # HTML templates for UI



---

## Setup & Running Locally

1. **Clone the repository**

    `git clone https://github.com/JamesPraneeth/fitness_tracker.git`
    
    `cd fitness_tracker`


2. **Create Python virtual environment**

    `python -m venv venv`
    
    `source venv/bin/activate # On Windows: venv\Scripts\activate`

3. **Install dependencies**

    `pip install -r requirements.txt`


4. **Configure environment variables**  

    Create a `.env` file to store sensitive configs in the rood directory:
    
    `GEMINI_API_KEY=your_google_gemini_api_key`
    
    `SECRET_KEY=your_flask_secret_key`


5. **Run the app**

    `python app.py`


6. **Access app through browser**  

    Go to `http://127.0.0.1:5000/`

---
**Video Demo of the App**

[Watch the video](https://github.com/JamesPraneeth/fitness_tracker/blob/main/media/demo.mp4)


Author

Developed by Praneeth

License

This project is open source and licensed under MIT License.
