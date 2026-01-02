from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps
from datetime import datetime
from config import Config
from models import db, User, Student, Company, PlacementDrive, Application

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ==================== DECORATORS ====================

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def company_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'company':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# ==================== AUTH ROUTES ====================

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'company':
            return redirect(url_for('company_dashboard'))
        elif current_user.role == 'student':
            return redirect(url_for('student_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact admin.', 'danger')
                return redirect(url_for('login'))
            
            # Check if company is approved
            if user.role == 'company':
                company = Company.query.filter_by(user_id=user.id).first()
                if company and company.approval_status != 'approved':
                    flash('Your company registration is pending approval.', 'warning')
                    return redirect(url_for('login'))
                if company and company.is_blacklisted:
                    flash('Your company has been blacklisted. Please contact admin.', 'danger')
                    return redirect(url_for('login'))
            
            # Check if student is blacklisted
            if user.role == 'student':
                student = Student.query.filter_by(user_id=user.id).first()
                if student and student.is_blacklisted:
                    flash('Your account has been blacklisted. Please contact admin.', 'danger')
                    return redirect(url_for('login'))
            
            login_user(user)
            flash('Login successful!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('auth/login.html')

@app.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        name = request.form.get('name')
        roll_number = request.form.get('roll_number')
        phone = request.form.get('phone')
        branch = request.form.get('branch')
        cgpa = request.form.get('cgpa', 0.0)
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register_student'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register_student'))
        
        if Student.query.filter_by(roll_number=roll_number).first():
            flash('Roll number already registered.', 'danger')
            return redirect(url_for('register_student'))
        
        # Create user
        user = User(email=email, role='student')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        # Create student profile
        student = Student(
            user_id=user.id,
            name=name,
            roll_number=roll_number,
            phone=phone,
            branch=branch,
            cgpa=float(cgpa) if cgpa else 0.0
        )
        db.session.add(student)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register_student.html')

@app.route('/register/company', methods=['GET', 'POST'])
def register_company():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        name = request.form.get('name')
        hr_name = request.form.get('hr_name')
        hr_email = request.form.get('hr_email')
        hr_phone = request.form.get('hr_phone')
        website = request.form.get('website')
        description = request.form.get('description')
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return redirect(url_for('register_company'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('register_company'))
        
        # Create user
        user = User(email=email, role='company')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        # Create company profile
        company = Company(
            user_id=user.id,
            name=name,
            hr_name=hr_name,
            hr_email=hr_email,
            hr_phone=hr_phone,
            website=website,
            description=description,
            approval_status='pending'
        )
        db.session.add(company)
        db.session.commit()
        
        flash('Registration successful! Please wait for admin approval.', 'success')
        return redirect(url_for('login'))
    
    return render_template('auth/register_company.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# ==================== ADMIN ROUTES ====================

@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    total_students = Student.query.count()
    total_companies = Company.query.count()
    total_drives = PlacementDrive.query.count()
    total_applications = Application.query.count()
    pending_companies = Company.query.filter_by(approval_status='pending').count()
    pending_drives = PlacementDrive.query.filter_by(status='pending').count()
    
    return render_template('admin/dashboard.html',
                           total_students=total_students,
                           total_companies=total_companies,
                           total_drives=total_drives,
                           total_applications=total_applications,
                           pending_companies=pending_companies,
                           pending_drives=pending_drives)

@app.route('/admin/companies')
@login_required
@admin_required
def admin_companies():
    search = request.args.get('search', '')
    if search:
        companies = Company.query.filter(Company.name.ilike(f'%{search}%')).all()
    else:
        companies = Company.query.all()
    return render_template('admin/companies.html', companies=companies, search=search)

@app.route('/admin/companies/<int:id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_company(id):
    company = Company.query.get_or_404(id)
    company.approval_status = 'approved'
    db.session.commit()
    flash(f'Company "{company.name}" has been approved.', 'success')
    return redirect(url_for('admin_companies'))

@app.route('/admin/companies/<int:id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_company(id):
    company = Company.query.get_or_404(id)
    company.approval_status = 'rejected'
    db.session.commit()
    flash(f'Company "{company.name}" has been rejected.', 'warning')
    return redirect(url_for('admin_companies'))

@app.route('/admin/companies/<int:id>/blacklist', methods=['POST'])
@login_required
@admin_required
def blacklist_company(id):
    company = Company.query.get_or_404(id)
    company.is_blacklisted = not company.is_blacklisted
    db.session.commit()
    status = 'blacklisted' if company.is_blacklisted else 'removed from blacklist'
    flash(f'Company "{company.name}" has been {status}.', 'info')
    return redirect(url_for('admin_companies'))

@app.route('/admin/companies/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_company(id):
    company = Company.query.get_or_404(id)
    user = User.query.get(company.user_id)
    db.session.delete(company)
    if user:
        db.session.delete(user)
    db.session.commit()
    flash('Company has been deleted.', 'success')
    return redirect(url_for('admin_companies'))

@app.route('/admin/students')
@login_required
@admin_required
def admin_students():
    search = request.args.get('search', '')
    if search:
        students = Student.query.filter(
            (Student.name.ilike(f'%{search}%')) |
            (Student.roll_number.ilike(f'%{search}%')) |
            (Student.phone.ilike(f'%{search}%'))
        ).all()
    else:
        students = Student.query.all()
    return render_template('admin/students.html', students=students, search=search)

@app.route('/admin/students/<int:id>/blacklist', methods=['POST'])
@login_required
@admin_required
def blacklist_student(id):
    student = Student.query.get_or_404(id)
    student.is_blacklisted = not student.is_blacklisted
    db.session.commit()
    status = 'blacklisted' if student.is_blacklisted else 'removed from blacklist'
    flash(f'Student "{student.name}" has been {status}.', 'info')
    return redirect(url_for('admin_students'))

@app.route('/admin/students/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_student(id):
    student = Student.query.get_or_404(id)
    user = User.query.get(student.user_id)
    db.session.delete(student)
    if user:
        db.session.delete(user)
    db.session.commit()
    flash('Student has been deleted.', 'success')
    return redirect(url_for('admin_students'))

@app.route('/admin/students/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_student(id):
    student = Student.query.get_or_404(id)
    if request.method == 'POST':
        student.name = request.form.get('name')
        student.phone = request.form.get('phone')
        student.branch = request.form.get('branch')
        student.cgpa = float(request.form.get('cgpa', 0))
        db.session.commit()
        flash('Student updated successfully.', 'success')
        return redirect(url_for('admin_students'))
    return render_template('admin/edit_student.html', student=student)

@app.route('/admin/drives')
@login_required
@admin_required
def admin_drives():
    drives = PlacementDrive.query.all()
    return render_template('admin/drives.html', drives=drives)

@app.route('/admin/drives/<int:id>/approve', methods=['POST'])
@login_required
@admin_required
def approve_drive(id):
    drive = PlacementDrive.query.get_or_404(id)
    drive.status = 'approved'
    db.session.commit()
    flash(f'Placement drive "{drive.job_title}" has been approved.', 'success')
    return redirect(url_for('admin_drives'))

@app.route('/admin/drives/<int:id>/reject', methods=['POST'])
@login_required
@admin_required
def reject_drive(id):
    drive = PlacementDrive.query.get_or_404(id)
    drive.status = 'rejected'
    db.session.commit()
    flash(f'Placement drive "{drive.job_title}" has been rejected.', 'warning')
    return redirect(url_for('admin_drives'))

@app.route('/admin/applications')
@login_required
@admin_required
def admin_applications():
    applications = Application.query.all()
    return render_template('admin/applications.html', applications=applications)

# ==================== COMPANY ROUTES ====================

@app.route('/company/dashboard')
@login_required
@company_required
def company_dashboard():
    company = Company.query.filter_by(user_id=current_user.id).first()
    drives = PlacementDrive.query.filter_by(company_id=company.id).all()
    total_applications = sum(drive.applications.count() for drive in drives)
    
    return render_template('company/dashboard.html',
                           company=company,
                           drives=drives,
                           total_applications=total_applications)

@app.route('/company/profile', methods=['GET', 'POST'])
@login_required
@company_required
def company_profile():
    company = Company.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        company.name = request.form.get('name')
        company.hr_name = request.form.get('hr_name')
        company.hr_email = request.form.get('hr_email')
        company.hr_phone = request.form.get('hr_phone')
        company.website = request.form.get('website')
        company.description = request.form.get('description')
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('company_profile'))
    
    return render_template('company/profile.html', company=company)

@app.route('/company/drives')
@login_required
@company_required
def company_drives():
    company = Company.query.filter_by(user_id=current_user.id).first()
    drives = PlacementDrive.query.filter_by(company_id=company.id).all()
    return render_template('company/drives.html', drives=drives)

@app.route('/company/drives/create', methods=['GET', 'POST'])
@login_required
@company_required
def create_drive():
    company = Company.query.filter_by(user_id=current_user.id).first()
    
    if company.approval_status != 'approved':
        flash('Your company must be approved before creating drives.', 'danger')
        return redirect(url_for('company_dashboard'))
    
    if request.method == 'POST':
        drive = PlacementDrive(
            company_id=company.id,
            job_title=request.form.get('job_title'),
            job_description=request.form.get('job_description'),
            eligibility_criteria=request.form.get('eligibility_criteria'),
            min_cgpa=float(request.form.get('min_cgpa', 0)),
            branches_allowed=request.form.get('branches_allowed'),
            package_lpa=float(request.form.get('package_lpa', 0)),
            application_deadline=datetime.strptime(request.form.get('application_deadline'), '%Y-%m-%d') if request.form.get('application_deadline') else None,
            status='pending'
        )
        db.session.add(drive)
        db.session.commit()
        flash('Placement drive created successfully. Waiting for admin approval.', 'success')
        return redirect(url_for('company_drives'))
    
    return render_template('company/create_drive.html')

@app.route('/company/drives/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@company_required
def edit_drive(id):
    company = Company.query.filter_by(user_id=current_user.id).first()
    drive = PlacementDrive.query.get_or_404(id)
    
    if drive.company_id != company.id:
        abort(403)
    
    if request.method == 'POST':
        drive.job_title = request.form.get('job_title')
        drive.job_description = request.form.get('job_description')
        drive.eligibility_criteria = request.form.get('eligibility_criteria')
        drive.min_cgpa = float(request.form.get('min_cgpa', 0))
        drive.branches_allowed = request.form.get('branches_allowed')
        drive.package_lpa = float(request.form.get('package_lpa', 0))
        drive.application_deadline = datetime.strptime(request.form.get('application_deadline'), '%Y-%m-%d') if request.form.get('application_deadline') else None
        db.session.commit()
        flash('Placement drive updated successfully.', 'success')
        return redirect(url_for('company_drives'))
    
    return render_template('company/edit_drive.html', drive=drive)

@app.route('/company/drives/<int:id>/close', methods=['POST'])
@login_required
@company_required
def close_drive(id):
    company = Company.query.filter_by(user_id=current_user.id).first()
    drive = PlacementDrive.query.get_or_404(id)
    
    if drive.company_id != company.id:
        abort(403)
    
    drive.status = 'closed'
    db.session.commit()
    flash('Placement drive has been closed.', 'info')
    return redirect(url_for('company_drives'))

@app.route('/company/drives/<int:id>/delete', methods=['POST'])
@login_required
@company_required
def delete_drive(id):
    company = Company.query.filter_by(user_id=current_user.id).first()
    drive = PlacementDrive.query.get_or_404(id)
    
    if drive.company_id != company.id:
        abort(403)
    
    db.session.delete(drive)
    db.session.commit()
    flash('Placement drive has been deleted.', 'success')
    return redirect(url_for('company_drives'))

@app.route('/company/drives/<int:id>/applications')
@login_required
@company_required
def drive_applications(id):
    company = Company.query.filter_by(user_id=current_user.id).first()
    drive = PlacementDrive.query.get_or_404(id)
    
    if drive.company_id != company.id:
        abort(403)
    
    applications = Application.query.filter_by(drive_id=drive.id).all()
    return render_template('company/applications.html', drive=drive, applications=applications)

@app.route('/company/applications/<int:id>/status', methods=['POST'])
@login_required
@company_required
def update_application_status(id):
    application = Application.query.get_or_404(id)
    company = Company.query.filter_by(user_id=current_user.id).first()
    
    if application.drive.company_id != company.id:
        abort(403)
    
    new_status = request.form.get('status')
    if new_status in ['applied', 'shortlisted', 'selected', 'rejected']:
        application.status = new_status
        db.session.commit()
        flash(f'Application status updated to {new_status}.', 'success')
    
    return redirect(url_for('drive_applications', id=application.drive_id))

# ==================== STUDENT ROUTES ====================

@app.route('/student/dashboard')
@login_required
@student_required
def student_dashboard():
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    # Get approved drives
    approved_drives = PlacementDrive.query.filter_by(status='approved').all()
    
    # Get student's applications
    applications = Application.query.filter_by(student_id=student.id).all()
    applied_drive_ids = [app.drive_id for app in applications]
    
    return render_template('student/dashboard.html',
                           student=student,
                           approved_drives=approved_drives,
                           applications=applications,
                           applied_drive_ids=applied_drive_ids)

@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
@student_required
def student_profile():
    student = Student.query.filter_by(user_id=current_user.id).first()
    
    if request.method == 'POST':
        student.name = request.form.get('name')
        student.phone = request.form.get('phone')
        student.branch = request.form.get('branch')
        student.cgpa = float(request.form.get('cgpa', 0))
        student.resume_url = request.form.get('resume_url')
        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('student_profile'))
    
    return render_template('student/profile.html', student=student)

@app.route('/student/drives')
@login_required
@student_required
def student_drives():
    student = Student.query.filter_by(user_id=current_user.id).first()
    drives = PlacementDrive.query.filter_by(status='approved').all()
    
    # Get applied drive IDs
    applications = Application.query.filter_by(student_id=student.id).all()
    applied_drive_ids = [app.drive_id for app in applications]
    
    return render_template('student/drives.html', 
                           drives=drives, 
                           applied_drive_ids=applied_drive_ids,
                           student=student)

@app.route('/student/drives/<int:id>/apply', methods=['POST'])
@login_required
@student_required
def apply_drive(id):
    student = Student.query.filter_by(user_id=current_user.id).first()
    drive = PlacementDrive.query.get_or_404(id)
    
    # Check if drive is approved
    if drive.status != 'approved':
        flash('This drive is not available for applications.', 'danger')
        return redirect(url_for('student_drives'))
    
    # Check if already applied
    existing = Application.query.filter_by(student_id=student.id, drive_id=drive.id).first()
    if existing:
        flash('You have already applied to this drive.', 'warning')
        return redirect(url_for('student_drives'))
    
    # Check eligibility (CGPA)
    if student.cgpa < drive.min_cgpa:
        flash(f'You do not meet the minimum CGPA requirement of {drive.min_cgpa}.', 'danger')
        return redirect(url_for('student_drives'))
    
    # Create application
    application = Application(
        student_id=student.id,
        drive_id=drive.id,
        status='applied'
    )
    db.session.add(application)
    db.session.commit()
    flash(f'Successfully applied to {drive.job_title}!', 'success')
    return redirect(url_for('student_drives'))

@app.route('/student/history')
@login_required
@student_required
def student_history():
    student = Student.query.filter_by(user_id=current_user.id).first()
    applications = Application.query.filter_by(student_id=student.id).order_by(Application.applied_at.desc()).all()
    return render_template('student/history.html', applications=applications)

# ==================== ERROR HANDLERS ====================

@app.errorhandler(403)
def forbidden(e):
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('errors/404.html'), 404

# ==================== MAIN ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create admin if not exists
        admin = User.query.filter_by(email='admin@portal.com').first()
        if not admin:
            admin = User(email='admin@portal.com', role='admin', is_active=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: admin@portal.com / admin123")
    
    app.run(debug=True)
