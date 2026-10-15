from flask import render_template, request, redirect, session, url_for, flash, jsonify, json
from .models import db, User, Stage, Country, Grade, StageCountry
from .forms import LoginForm, GradeForm
from .country_flags import country_flags, get_flag_emoji
from datetime import datetime
import csv
import io

def configure_routes(app):
    # Register all routes with the app
    @app.route('/logout')
    def logout():
        session.pop('user_id', None)
        flash('You have been logged out.')
        return redirect(url_for('index'))

    # Update existing routes to handle login status appropriately
    @app.route('/', methods=['GET', 'POST'])
    def index():
        form = LoginForm()
        if form.validate_on_submit():
            username = form.username.data
            
            # Clear any existing session data
            session.pop('user_id', None)
            session.pop('username', None)
            
            # Find or create user
            user = User.query.filter_by(username=username).first()
            if not user:
                try:
                    user = User(username=username)
                    db.session.add(user)
                    db.session.commit()
                    flash(f"Welcome, {username}! Your account has been created.", "success")
                except Exception as e:
                    db.session.rollback()
                    flash("Could not create user", "danger")
                    return render_template('index.html', form=form, stages=[])
            
            # Store user info in session
            session['user_id'] = user.id
            session['username'] = username
            flash(f"Welcome back, {username}!", "success")
            
        stages = Stage.query.all()
        return render_template('index.html', form=form, stages=stages)

    @app.route('/stage/<int:stage_id>')
    def stage(stage_id):
        if 'user_id' not in session:
            flash("Please log in to view stages", "warning")
            return redirect(url_for('index'))

        # Verify user exists
        user_id = session['user_id']
        user = User.query.get(user_id)
        if not user:
            flash("Your session has expired. Please log in again.", "danger")
            session.pop('user_id', None)
            session.pop('username', None)
            return redirect(url_for('index'))

        stage = Stage.query.get_or_404(stage_id)

        # Latest grades by country for this user/stage
        latest = (
            db.session.query(
                Grade.country_id,
                db.func.max(Grade.timestamp).label('ts')
            )
            .filter_by(user_id=user_id, stage_id=stage_id)
            .group_by(Grade.country_id)
            .all()
        )
        grades = {}
        for country_id, ts in latest:
            g = Grade.query.filter_by(
                user_id=user_id,
                stage_id=stage_id,
                country_id=country_id,
                timestamp=ts
            ).first()
            if g:
                grades[country_id] = g.value

        # Fetch countries for this stage, ordered by performance order
        countries = (
            Country.query
            .join(StageCountry, Country.id == StageCountry.country_id)
            .filter(StageCountry.stage_id == stage_id)
            .order_by(StageCountry.order)
            .all()
        )

        # User votes count
        users = User.query.all()
        user_votes = {}
        for u in users:
            count = (
                Grade.query
                .filter_by(user_id=u.id, stage_id=stage_id)
                .distinct(Grade.country_id)
                .count()
            )
            user_votes[u.id] = count

        # User favorite country (highest grade)
        user_favorites = {}
        for u in users:
            fav = (
                db.session.query(Grade.country_id)
                .filter_by(user_id=u.id, stage_id=stage_id)
                .order_by(Grade.value.desc())
                .first()
            )
            if fav:
                user_favorites[u.id] = Country.query.get(fav.country_id)

        # Calculate rankings for this stage (sorted by total score)
        rankings = []
        for country in countries:
            total_grade = 0
            
            # Get all users
            all_users = User.query.all()
            
            for u in all_users:
                # Get the latest grade from this user for this country
                latest_grade = db.session.query(
                    Grade
                ).filter_by(
                    user_id=u.id,
                    stage_id=stage_id,
                    country_id=country.id
                ).order_by(
                    Grade.timestamp.desc()
                ).first()
                
                if latest_grade:
                    total_grade += latest_grade.value
            
            if total_grade > 0:
                rankings.append((country, total_grade))
        
        # Sort rankings by total grade (highest first)
        ranking_items = sorted(rankings, key=lambda x: x[1], reverse=True)
        
        return render_template('stage.html',
                            stage=stage,
                            countries=countries,
                            grades=grades,
                            users=users,
                            user_votes=user_votes,
                            user_favorites=user_favorites,
                            country_flags=country_flags,
                            ranking_items=ranking_items)

  
    @app.route('/fill-db', methods=['GET', 'POST'])
    def fill_db():
        # Check if user is admin (for simplicity, we'll just check if they're logged in)
        if 'user_id' not in session:
            flash("You need to be logged in to access this page", "warning")
            return redirect(url_for('index'))
            
        # Verify user exists in database
        user_id = session['user_id']
        user = User.query.get(user_id)
        if not user:
            flash("Your session has expired. Please log in again.", "danger")
            session.pop('user_id', None)
            session.pop('username', None)
            return redirect(url_for('index'))
            
        # Initialize variables for template
        preview_data = None
        selected_stage = None
        clear_existing = False
        csv_data_json = None
        
        if request.method == 'POST':
            # Get form data
            stage_id = request.form.get('stage')
            clear_existing = 'clear_existing' in request.form
            
            # Map stage_id to actual stage names
            stage_map = {
                'semi1': 'Semi-final 1',
                'semi2': 'Semi-final 2',
                'final': 'Final'
            }
            
            selected_stage = stage_id
            stage_name = stage_map.get(stage_id)
            
            if not stage_name:
                flash("Invalid stage selected", "danger")
                return redirect(url_for('fill_db'))
                
            # Get CSV data from textarea
            csv_data_text = request.form.get('csv_data')
            
            if not csv_data_text or csv_data_text.strip() == '':
                flash("No CSV data provided", "danger")
                return redirect(url_for('fill_db'))
                
            # Read and validate CSV
            try:
                # Read CSV data from textarea
                stream = io.StringIO(csv_data_text, newline=None)
                csv_data = list(csv.DictReader(stream))
                
                # Validate CSV structure
                required_fields = ['position', 'country', 'artist', 'song']
                for field in required_fields:
                    if not all(field in row for row in csv_data):
                        flash(f"CSV is missing required field: {field}", "danger")
                        return redirect(url_for('fill_db'))
                
                # Prepare preview data
                preview_data = csv_data
                csv_data_json = json.dumps(csv_data)
                
                flash(f"CSV file validated successfully. {len(csv_data)} entries found.", "success")
                
            except Exception as e:
                flash(f"Error processing CSV file: {str(e)}", "danger")
                return redirect(url_for('fill_db'))
        
        return render_template('fill_db.html',
                              preview_data=preview_data,
                              selected_stage=selected_stage,
                              clear_existing=clear_existing,
                              csv_data_json=csv_data_json,
                              country_flags=country_flags)
    
    @app.route('/confirm-fill-db', methods=['POST'])
    def confirm_fill_db():
        if 'user_id' not in session:
            flash("You need to be logged in to access this page", "warning")
            return redirect(url_for('index'))
            
        # Verify user exists in database
        user_id = session['user_id']
        user = User.query.get(user_id)
        if not user:
            flash("Your session has expired. Please log in again.", "danger")
            session.pop('user_id', None)
            session.pop('username', None)
            return redirect(url_for('index'))
            
        # Get form data
        stage_id = request.form.get('stage')
        clear_existing = request.form.get('clear_existing') == 'True'
        csv_data_json = request.form.get('csv_data')
        
        if not csv_data_json:
            flash("No data provided", "danger")
            return redirect(url_for('fill_db'))
            
        try:
            # Parse JSON data
            csv_data = json.loads(csv_data_json)
            
            # Map stage_id to actual stage names
            stage_map = {
                'semi1': 'Semi-final 1',
                'semi2': 'Semi-final 2',
                'final': 'Final'
            }
            
            stage_name = stage_map.get(stage_id)
            
            if not stage_name:
                flash("Invalid stage selected", "danger")
                return redirect(url_for('fill_db'))
                
            # Get or create stage
            stage = Stage.query.filter_by(display_name=stage_name).first()
            if not stage:
                stage = Stage(display_name=stage_name)
                db.session.add(stage)
                db.session.commit()
                
            # Clear existing countries if requested
            if clear_existing:
                # Get all countries in this stage
                stage_countries = StageCountry.query.filter_by(stage_id=stage.id).all()
                
                # Remove countries from stage
                for sc in stage_countries:
                    db.session.delete(sc)
                    
                db.session.commit()
                flash(f"Cleared existing countries from {stage_name}", "info")
            
            # Add countries from CSV
            countries_added = 0
            for row in csv_data:
                country_name = row['country'].strip()
                artist = row['artist'].strip()
                song = row['song'].strip()
                
                # Get position from CSV (or use index+1 if not provided or invalid)
                try:
                    position = int(row['position'].strip())
                    if position < 1:
                        position = countries_added + 1
                except (ValueError, KeyError):
                    position = countries_added + 1
                
                # Check if country already exists
                country = Country.query.filter_by(display_name=country_name).first()
                
                if not country:
                    # Create new country
                    country = Country(display_name=country_name, artist=artist, song=song)
                    db.session.add(country)
                else:
                    # Update existing country
                    country.artist = artist
                    country.song = song
                
                # Add country to stage if not already there
                existing_stage_country = StageCountry.query.filter_by(
                    stage_id=stage.id,
                    country_id=country.id
                ).first()
                
                if not existing_stage_country:
                    # Create new association with order from CSV
                    new_stage_country = StageCountry(
                        stage_id=stage.id,
                        country_id=country.id,
                        order=position
                    )
                    db.session.add(new_stage_country)
                    countries_added += 1
                else:
                    # Update existing association with new order
                    existing_stage_country.order = position
            
            db.session.commit()
            flash(f"Successfully added {countries_added} countries to {stage_name}", "success")
            
            return redirect(url_for('stage', stage_id=stage.id))
            
        except Exception as e:
            flash("Could not save data", "danger")
            return redirect(url_for('fill_db'))

    @app.route('/stage/<int:stage_id>/submit/<int:country_id>', methods=['POST'])
    def submit_grades(stage_id, country_id):
        if 'user_id' not in session:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': "Please log in to vote"})
            flash("Please log in to vote", "warning")
            return redirect(url_for('index'))

        user_id = session['user_id']
        
        # Verify user exists in database
        user = User.query.get(user_id)
        if not user:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': "User not found. Please log in again."})
            flash("User not found. Please log in again.", "danger")
            session.pop('user_id', None)
            session.pop('username', None)
            return redirect(url_for('index'))
        # Convert grade_value to integer
        try:
            grade_value = int(request.form.get('grade'))
            # Validate grade is within allowed range
            if not 1 <= grade_value <= 12:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'message': "Grade must be between 1 and 12"})
                flash("Grade must be between 1 and 12", "danger")
                return redirect(url_for('stage', stage_id=stage_id))
        except (ValueError, TypeError):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': "Invalid grade value"})
            flash("Invalid grade value", "danger")
            return redirect(url_for('stage', stage_id=stage_id))

        if not StageCountry.query.filter_by(stage_id=stage_id, country_id=country_id).first():
            return jsonify({'success': False, 'message': 'Country is not in this stage'}), 404

        # Always create a new grade with the current timestamp
        # This ensures we have a history of all votes and can get the latest one
        new_grade = Grade(
            user_id=user_id,
            stage_id=stage_id,
            country_id=country_id,
            value=grade_value,
            timestamp=datetime.utcnow()
        )
        db.session.add(new_grade)

        db.session.commit()
        
        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Get updated rankings for this stage using the same logic as in the stage route
            rankings = []
            
            # Get all countries in this stage
            countries_in_stage = Country.query.join(StageCountry).filter(StageCountry.stage_id == stage_id).all()
            
            for country in countries_in_stage:
                total_grade = 0
                
                # Get all users
                all_users = User.query.all()
                
                for user in all_users:
                    # Get the latest grade from this user for this country
                    latest_grade = db.session.query(
                        Grade
                    ).filter_by(
                        user_id=user.id,
                        stage_id=stage_id,
                        country_id=country.id
                    ).order_by(
                        Grade.timestamp.desc()
                    ).first()
                    
                    if latest_grade:
                        total_grade += latest_grade.value
                
                if total_grade > 0:
                    rankings.append((country.id, total_grade))
            
            # Sort rankings by total grade (highest first)
            rankings.sort(key=lambda x: x[1], reverse=True)

            
            # Format rankings for JSON response
            rankings_data = [{'country_id': country_id, 'total_grade': total_grade}
                            for country_id, total_grade in rankings]
            
            return jsonify({
                'success': True,
                'message': "Your vote has been recorded!",
                'rankings': rankings_data
            })
            
        flash("Your vote has been recorded!", "success")
        return redirect(url_for('stage', stage_id=stage_id))
        
    @app.route('/stage/<int:stage_id>/user/<int:user_id>')
    def user_votes(stage_id, user_id):
        if 'user_id' not in session:
            flash("Please log in to view user votes", "warning")
            return redirect(url_for('index'))
            
        # Verify current user exists in database
        current_user = User.query.get(session['user_id'])
        if not current_user:
            flash("Your session has expired. Please log in again.", "danger")
            session.pop('user_id', None)
            session.pop('username', None)
            return redirect(url_for('index'))
            
        stage = Stage.query.get_or_404(stage_id)
        
        # Verify requested user exists
        user = User.query.get(user_id)
        if not user:
            flash("The requested user does not exist.", "danger")
            return redirect(url_for('stage', stage_id=stage_id))
        
        # Get all grades for this user in this stage, ensuring no duplicates
        # Use distinct to get only the latest grade for each country
        latest_grades = db.session.query(
            Grade.country_id,
            db.func.max(Grade.timestamp).label('latest_timestamp')
        ).filter_by(
            user_id=user_id,
            stage_id=stage_id
        ).group_by(Grade.country_id).all()
        
        # Create a list of (country, grade) tuples
        user_grades = []
        for country_id, latest_timestamp in latest_grades:
            # Get the grade with the latest timestamp
            grade = Grade.query.filter_by(
                user_id=user_id,
                stage_id=stage_id,
                country_id=country_id,
                timestamp=latest_timestamp
            ).first()
            
            if grade:
                country = Country.query.get(grade.country_id)
                user_grades.append((country, grade.value))
            
        # Sort by grade value (highest first)
        user_grades.sort(key=lambda x: x[1], reverse=True)
        
        return render_template('user_votes.html',
                              user=user,
                              stage=stage,
                              user_grades=user_grades,
                              country_flags=country_flags)
                              
    @app.route('/stage/<int:stage_id>/update_order/<int:country_id>', methods=['POST'])
    def update_country_order(stage_id, country_id):
        if 'user_id' not in session:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': "Please log in to update order"})
            flash("Please log in to update order", "warning")
            return redirect(url_for('index'))

        user_id = session['user_id']
        
        # Verify user exists in database
        user = User.query.get(user_id)
        if not user:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': "User not found. Please log in again."})
            flash("User not found. Please log in again.", "danger")
            session.pop('user_id', None)
            session.pop('username', None)
            return redirect(url_for('index'))
            
        # Get the new order value
        try:
            new_order = int(request.form.get('order'))
            if new_order < 1:
                raise ValueError("Order must be a positive number")
        except (ValueError, TypeError):
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': "Invalid order value"})
            flash("Invalid order value", "danger")
            return redirect(url_for('stage', stage_id=stage_id))
            
        # Find the stage-country association
        stage_country = StageCountry.query.filter_by(
            stage_id=stage_id,
            country_id=country_id
        ).first()
        
        if not stage_country:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': "Country not found in this stage"})
            flash("Country not found in this stage", "danger")
            return redirect(url_for('stage', stage_id=stage_id))
            
        # Update the order
        stage_country.order = new_order
        db.session.commit()
        
        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'message': "Order updated successfully"
            })
            
        flash("Order updated successfully", "success")
        return redirect(url_for('stage', stage_id=stage_id))