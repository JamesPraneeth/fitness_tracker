from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, IntegerField, SubmitField
from wtforms.validators import InputRequired, Email, Length
from datetime import datetime, date, timedelta, timezone
import os
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
import google.generativeai as genai
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv('api.env')

# Configure API keys from environment
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'YOUR_API_KEY_HERE')
genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-only-for-testing')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fitness_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ==================== MODELS ====================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    height = db.Column(db.Float, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    age = db.Column(db.Integer, default=25)
    gender = db.Column(db.String(10), default='male')
    activity_level = db.Column(db.String(20), default='moderate')
    goal = db.Column(db.String(20), default='maintain')

    calorie_goal = db.Column(db.Float, default=2000)
    protein_goal = db.Column(db.Float, default=150)
    carbs_goal = db.Column(db.Float, default=200)
    fats_goal = db.Column(db.Float, default=65)

    food_logs = db.relationship('FoodLog', backref='user', lazy=True, cascade='all, delete-orphan')
    workout_sessions = db.relationship('WorkoutSession', backref='user', lazy=True, cascade='all, delete-orphan')
    body_weight_logs = db.relationship('BodyWeightLog', backref='user', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.name}>'

class FoodLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    name = db.Column(db.String(100), nullable=False)
    calories = db.Column(db.Float, nullable=False)
    protein = db.Column(db.Float, nullable=False)
    carbs = db.Column(db.Float, nullable=False)
    fats = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<FoodLog {self.name}>'

class WorkoutSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    total_duration = db.Column(db.Integer)

    exercise_sets = db.relationship('ExerciseSet', backref='workout_session', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<WorkoutSession {self.id}>'

class ExerciseSet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    workout_session_id = db.Column(db.Integer, db.ForeignKey('workout_session.id'), nullable=False)
    exercise_name = db.Column(db.String(100), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    reps = db.Column(db.Integer, nullable=False)
    set_number = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<ExerciseSet {self.exercise_name}>'

class BodyWeightLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today)
    weight = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<BodyWeightLog {self.weight}kg>'

# ==================== ADMIN VIEWS ====================

class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        flash('You need admin privileges to access this page.')
        return redirect(url_for('login'))

class UserAdminView(SecureModelView):
    column_list = ('id', 'name', 'email', 'height', 'weight', 'is_admin', 'created_at')
    column_searchable_list = ('name', 'email')
    column_filters = ('is_admin', 'created_at')
    column_editable_list = ('name', 'height', 'weight', 'is_admin')
    form_excluded_columns = ('password_hash', 'food_logs', 'workout_sessions', 'body_weight_logs')

class FoodLogAdminView(SecureModelView):
    column_list = ('id', 'user', 'name', 'calories', 'protein', 'carbs', 'fats', 'date')
    column_searchable_list = ('name',)
    column_filters = ('date',)
    column_default_sort = ('date', True)

    def _user_formatter(view, context, model, name):
        if model.user:
            return model.user.name
        return ''

    column_formatters = {'user': _user_formatter}

class WorkoutSessionAdminView(SecureModelView):
    column_list = ('id', 'user', 'date', 'start_time', 'end_time', 'total_duration')
    column_filters = ('date',)
    column_default_sort = ('date', True)

    def _user_formatter(view, context, model, name):
        if model.user:
            return model.user.name
        return ''

    column_formatters = {'user': _user_formatter}

class ExerciseSetAdminView(SecureModelView):
    column_list = ('id', 'workout_session', 'exercise_name', 'weight', 'reps', 'set_number')
    column_searchable_list = ('exercise_name',)
    column_filters = ('exercise_name',)

    def _workout_formatter(view, context, model, name):
        if model.workout_session:
            return f"Session {model.workout_session.id} ({model.workout_session.date})"
        return ''

    column_formatters = {'workout_session': _workout_formatter}

class BodyWeightLogAdminView(SecureModelView):
    column_list = ('id', 'user', 'date', 'weight')
    column_filters = ('date',)
    column_default_sort = ('date', True)

    def _user_formatter(view, context, model, name):
        if model.user:
            return model.user.name
        return ''

    column_formatters = {'user': _user_formatter}

class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need admin privileges to access this page.')
            return redirect(url_for('login'))

        user_count = User.query.count()
        food_log_count = FoodLog.query.count()
        workout_count = WorkoutSession.query.count()

        return self.render('admin/custom_index.html',
                         user_count=user_count,
                         food_log_count=food_log_count,
                         workout_count=workout_count)

admin = Admin(app, name='Fitness Tracker Admin', template_mode='bootstrap4', index_view=MyAdminIndexView())
admin.add_view(UserAdminView(User, db.session, name='Users'))
admin.add_view(FoodLogAdminView(FoodLog, db.session, name='Food Logs'))
admin.add_view(WorkoutSessionAdminView(WorkoutSession, db.session, name='Workout Sessions'))
admin.add_view(ExerciseSetAdminView(ExerciseSet, db.session, name='Exercise Sets'))
admin.add_view(BodyWeightLogAdminView(BodyWeightLog, db.session, name='Body Weight Logs'))

# ==================== FORMS ====================

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[InputRequired(), Length(max=100)])
    email = StringField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=6)])
    age = IntegerField('Age', validators=[InputRequired()])
    gender = StringField('Gender')
    height = FloatField('Height (cm)', validators=[InputRequired()])
    weight = FloatField('Weight (kg)', validators=[InputRequired()])
    activity_level = StringField('Activity Level')
    goal = StringField('Goal')
    submit = SubmitField('Register')

class FoodForm(FlaskForm):
    name = StringField('Food Name', validators=[InputRequired()])
    calories = FloatField('Calories', validators=[InputRequired()])
    protein = FloatField('Protein (g)', validators=[InputRequired()])
    carbs = FloatField('Carbs (g)', validators=[InputRequired()])
    fats = FloatField('Fats (g)', validators=[InputRequired()])
    submit = SubmitField('Add Food')

class BodyWeightForm(FlaskForm):
    weight = FloatField('Weight (kg)', validators=[InputRequired()])
    submit = SubmitField('Add Weight')


def get_ai_recommendations(user):
    """Get personalized AI recommendations"""
    today = date.today()
    week_ago = today - timedelta()

    recent_foods = FoodLog.query.filter(
        FoodLog.user_id == user.id,
        FoodLog.date >= week_ago
    ).all()

    recent_workouts = WorkoutSession.query.filter(
        WorkoutSession.user_id == user.id,
        WorkoutSession.date >= week_ago
    ).all()

    if recent_foods:
        days_count = max(1, len(set(f.date for f in recent_foods)))
        avg_calories = sum(f.calories for f in recent_foods) / days_count
        avg_protein = sum(f.protein for f in recent_foods) / days_count
    else:
        avg_calories = 0
        avg_protein = 0

    workout_count = len(recent_workouts)

    prompt = f"""You are a fitness coach. Give 3 personalized tips.

User: {user.age}yr old {user.gender}, {user.height}cm, {user.weight}kg
Goals: {user.calorie_goal}cal/day, {user.protein_goal}g protein/day
Last week: {int(avg_calories)}cal/day avg, {int(avg_protein)}g protein/day avg, {workout_count} workouts

Return JSON only:
{{
  "recommendations": ["tip 1", "tip 2", "tip 3"]
}}"""

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)

        if hasattr(response, 'text'):
            text = response.text
        else:
            text = str(response)

        if not isinstance(text, str):
            text = str(text)

        text = text.strip()

        if '```json' in text:
            text = text.split('```json')[1].split('```')[0].strip()
        elif '```' in text:
            text = text.split('```')[1].split('```')[0].strip()

        result = json.loads(text)
        recommendations = result.get('recommendations', [])

        if recommendations and len(recommendations) >= 3:
            return recommendations[:3]
        else:
            return [
                "Track your daily nutrition consistently.",
                "Maintain regular workout schedule.",
                "Get 7-8 hours of sleep for recovery."
            ]
    except Exception as e:
        print(f"AI Error: {e}")
        return [
            "Track your daily nutrition consistently.",
            "Maintain regular workout schedule.",
            "Get 7-8 hours of sleep for recovery."
        ]

# ==================== MACRO CALCULATOR ====================

def calculate_user_macros(user):
    activity_multipliers = {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'active': 1.725,
        'very_active': 1.9
    }

    goal_adjustments = {
        'lose': -500,
        'maintain': 0,
        'gain': 300
    }

    if user.gender == 'male':
        bmr = (10 * user.weight) + (6.25 * user.height) - (5 * user.age) + 5
    else:
        bmr = (10 * user.weight) + (6.25 * user.height) - (5 * user.age) - 161

    activity_multiplier = activity_multipliers.get(user.activity_level, 1.55)
    tdee = bmr * activity_multiplier

    goal_adjustment = goal_adjustments.get(user.goal, 0)
    calorie_goal = tdee + goal_adjustment

    if user.goal == 'gain':
        protein_multiplier = 2.2
    elif user.goal == 'lose':
        protein_multiplier = 2.4
    else:
        protein_multiplier = 2.0

    protein_goal = user.weight * protein_multiplier
    fats_goal = (calorie_goal * 0.25) / 9

    protein_calories = protein_goal * 4
    fat_calories = fats_goal * 9
    remaining_calories = calorie_goal - protein_calories - fat_calories
    carbs_goal = remaining_calories / 4

    user.calorie_goal = round(calorie_goal)
    user.protein_goal = round(protein_goal, 1)
    user.carbs_goal = round(carbs_goal, 1)
    user.fats_goal = round(fats_goal, 1)

    db.session.commit()

    return {
        'bmr': round(bmr),
        'tdee': round(tdee),
        'calories': round(calorie_goal),
        'protein': round(protein_goal, 1),
        'carbs': round(carbs_goal, 1),
        'fats': round(fats_goal, 1)
    }

# ==================== USER LOADER ====================

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ==================== ROUTES ====================

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    food_logs = FoodLog.query.filter_by(user_id=current_user.id, date=today).all()

    total_calories = sum(log.calories for log in food_logs)
    total_protein = sum(log.protein for log in food_logs)
    total_carbs = sum(log.carbs for log in food_logs)
    total_fats = sum(log.fats for log in food_logs)

    workout_sessions = WorkoutSession.query.filter_by(user_id=current_user.id, date=today).all()
    exercise_logs = []

    for session in workout_sessions:
        for exercise_set in session.exercise_sets:
            exercise_logs.append({
                'exercise_name': exercise_set.exercise_name,
                'weight': exercise_set.weight,
                'reps': exercise_set.reps,
                'set_number': exercise_set.set_number
            })

    return render_template('dashboard.html',
                         food_logs=food_logs,
                         exercise_logs=exercise_logs,
                         total_calories=total_calories,
                         total_protein=total_protein,
                         total_carbs=total_carbs,
                         total_fats=total_fats,
                         calorie_goal=current_user.calorie_goal,
                         protein_goal=current_user.protein_goal,
                         carbs_goal=current_user.carbs_goal,
                         fats_goal=current_user.fats_goal,
                         today=today)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            if next_page and '/admin' in next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        flash('Invalid email or password')

    return render_template('login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email already registered')
            return render_template('register.html', form=form)

        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data),
            age=form.age.data,
            gender=form.gender.data,
            height=form.height.data,
            weight=form.weight.data,
            activity_level=form.activity_level.data,
            goal=form.goal.data,
            is_admin=False
        )

        db.session.add(new_user)
        db.session.commit()

        calculate_user_macros(new_user)

        login_user(new_user)
        flash('Registration successful! Your personalized macros have been calculated.')
        return redirect(url_for('dashboard'))

    return render_template('register.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@app.route('/profile/workout-history')
@login_required
def profile_workout_history():
    workout_sessions = WorkoutSession.query.filter_by(user_id=current_user.id).order_by(WorkoutSession.date.desc()).all()
    return render_template('profile_workout_history.html', workout_sessions=workout_sessions)

@app.route('/profile/food-logs')
@login_required
def profile_food_logs():
    food_logs = FoodLog.query.filter_by(user_id=current_user.id).order_by(FoodLog.date.desc()).all()
    weight_logs = BodyWeightLog.query.filter_by(user_id=current_user.id).order_by(BodyWeightLog.date.desc()).all()
    return render_template('profile_food_logs.html', food_logs=food_logs, weight_logs=weight_logs)

@app.route('/food-tracker', methods=['GET', 'POST'])
@login_required
def food_tracker():
    food_form = FoodForm()
    weight_form = BodyWeightForm()

    if food_form.validate_on_submit() and food_form.submit.data:
        new_food = FoodLog(
            user_id=current_user.id,
            name=food_form.name.data,
            calories=food_form.calories.data,
            protein=food_form.protein.data,
            carbs=food_form.carbs.data,
            fats=food_form.fats.data
        )
        db.session.add(new_food)
        db.session.commit()
        flash('Food logged successfully!')
        return redirect(url_for('food_tracker'))

    if weight_form.validate_on_submit() and weight_form.submit.data:
        new_weight = BodyWeightLog(
            user_id=current_user.id,
            weight=weight_form.weight.data
        )
        db.session.add(new_weight)

        old_weight = current_user.weight
        current_user.weight = weight_form.weight.data
        db.session.commit()

        calculate_user_macros(current_user)

        weight_change = weight_form.weight.data - old_weight
        if abs(weight_change) > 0.1:
            flash(f'Weight updated! Macros recalculated based on new weight ({weight_change:+.1f}kg change).')
        else:
            flash('Weight logged successfully!')
        return redirect(url_for('food_tracker'))

    today = date.today()
    food_logs = FoodLog.query.filter_by(user_id=current_user.id, date=today).all()
    weight_logs = BodyWeightLog.query.filter_by(user_id=current_user.id).order_by(BodyWeightLog.date.desc()).all()

    return render_template('food_tracker.html',
                         food_form=food_form,
                         weight_form=weight_form,
                         food_logs=food_logs,
                         weight_logs=weight_logs)

@app.route('/delete-food/<int:food_id>')
@login_required
def delete_food(food_id):
    food_log = db.session.get(FoodLog, food_id)
    if not food_log:
        abort(404)

    if food_log.user_id == current_user.id:
        db.session.delete(food_log)
        db.session.commit()
        flash('Food entry deleted!')

    return redirect(request.referrer or url_for('food_tracker'))

@app.route('/delete-weight/<int:weight_id>')
@login_required
def delete_weight(weight_id):
    weight_log = db.session.get(BodyWeightLog, weight_id)
    if not weight_log:
        abort(404)

    if weight_log.user_id == current_user.id:
        db.session.delete(weight_log)
        db.session.commit()
        flash('Weight entry deleted!')

    return redirect(request.referrer or url_for('food_tracker'))

@app.route('/workout-tracker')
@login_required
def workout_tracker():
    return render_template('workout_tracker.html')

@app.route('/start-workout', methods=['POST'])
@login_required
def start_workout():
    new_session = WorkoutSession(
        user_id=current_user.id,
        start_time=datetime.now(timezone.utc)
    )
    db.session.add(new_session)
    db.session.commit()
    return jsonify({'session_id': new_session.id, 'status': 'started'})

@app.route('/add-exercise', methods=['POST'])
@login_required
def add_exercise():
    data = request.get_json()
    session_id = data.get('session_id')
    exercise_name = data.get('exercise_name')
    weight = data.get('weight')
    reps = data.get('reps')
    set_number = data.get('set_number')

    new_set = ExerciseSet(
        workout_session_id=session_id,
        exercise_name=exercise_name,
        weight=weight,
        reps=reps,
        set_number=set_number
    )
    db.session.add(new_set)
    db.session.commit()

    return jsonify({'status': 'success', 'set_id': new_set.id})

@app.route('/finish-workout', methods=['POST'])
@login_required
def finish_workout():
    data = request.get_json()
    session_id = data.get('session_id')
    duration = data.get('duration')

    session = db.session.get(WorkoutSession, session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    session.end_time = datetime.now(timezone.utc)
    session.total_duration = duration
    db.session.commit()

    return jsonify({'status': 'finished'})

@app.route('/delete-exercise-set/<int:set_id>')
@login_required
def delete_exercise_set(set_id):
    exercise_set = db.session.get(ExerciseSet, set_id)
    if not exercise_set:
        abort(404)

    if exercise_set.workout_session.user_id == current_user.id:
        db.session.delete(exercise_set)
        db.session.commit()
        flash('Exercise set deleted!')

    return redirect(request.referrer or url_for('workout_tracker'))

@app.route('/delete-workout-session/<int:session_id>')
@login_required
def delete_workout_session(session_id):
    workout_session = db.session.get(WorkoutSession, session_id)
    if not workout_session:
        abort(404)

    if workout_session.user_id == current_user.id:
        db.session.delete(workout_session)
        db.session.commit()
        flash('Workout session deleted!')

    return redirect(request.referrer or url_for('profile_workout_history'))

@app.route('/ai-coach')
@login_required
def ai_coach():
    recommendations = get_ai_recommendations(current_user)
    return render_template('ai_coach.html', recommendations=recommendations)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        current_user.weight = float(request.form.get('weight'))
        current_user.activity_level = request.form.get('activity_level')
        current_user.goal = request.form.get('goal')

        macros = calculate_user_macros(current_user)

        flash(f'Settings updated! New macro goals: {macros["calories"]} cal, {macros["protein"]}g protein, {macros["carbs"]}g carbs, {macros["fats"]}g fats')
        return redirect(url_for('settings'))

    return render_template('settings.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        admin_user = User.query.filter_by(email='admin@fitness.com').first()
        if not admin_user:
            admin_user = User(
                name='Admin',
                email='admin@fitness.com',
                password_hash=generate_password_hash('admin123'),
                age=30,
                gender='male',
                height=175,
                weight=70,
                activity_level='moderate',
                goal='maintain',
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin user created: admin@fitness.com / admin123")

    app.run(debug=True)



