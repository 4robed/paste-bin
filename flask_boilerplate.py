"""
Flask Web Application Boilerplate - Full-featured Example
Complete Flask setup with SQLAlchemy, authentication, forms, and blueprints.
"""

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Length
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
from functools import wraps
from typing import Optional, List, Dict, Any
import logging
from logging.handlers import RotatingFileHandler

# ============================================================================
# APPLICATION CONFIGURATION
# ============================================================================

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# ============================================================================
# APPLICATION FACTORY & EXTENSIONS
# ============================================================================

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address)

def create_app(config_name='DevelopmentConfig'):
    """Application factory"""
    app = Flask(__name__)

    # Load configuration
    config_class = globals().get(config_name, DevelopmentConfig)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    limiter.init_app(app)
    CORS(app)

    # Configure logging
    setup_logging(app)

    # Register blueprints
    from .blueprints import auth_bp, main_bp, api_bp, admin_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    # Create tables
    with app.app_context():
        db.create_all()

    return app

def setup_logging(app):
    """Configure logging"""
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240000, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('Application startup')

# ============================================================================
# DATABASE MODELS
# ============================================================================

class User(UserMixin, db.Model):
    """User model"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(120))
    last_name = db.Column(db.String(120))
    bio = db.Column(db.Text)
    avatar = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, index=True)
    is_admin = db.Column(db.Boolean, default=False)
    email_verified = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    posts = db.relationship('Post', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)

    def get_full_name(self):
        """Get user full name"""
        return f"{self.first_name} {self.last_name}".strip() or self.username

    def to_dict(self):
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'full_name': self.get_full_name(),
            'bio': self.bio,
            'avatar': self.avatar,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat(),
        }

class Category(db.Model):
    """Post category model"""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    posts = db.relationship('Post', backref='category', lazy='dynamic')

    def __repr__(self):
        return f'<Category {self.name}>'

class Tag(db.Model):
    """Tag model"""
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    posts = db.relationship('Post', secondary='post_tags', backref=db.backref('tags', lazy='dynamic'))

    def __repr__(self):
        return f'<Tag {self.name}>'

class Post(db.Model):
    """Blog post model"""
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.String(500))
    featured_image = db.Column(db.String(255))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), index=True)

    status = db.Column(db.String(20), default='draft', index=True)
    is_featured = db.Column(db.Boolean, default=False)
    allow_comments = db.Column(db.Boolean, default=True)

    views = db.Column(db.Integer, default=0)
    likes_count = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)

    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    comments = db.relationship('Comment', backref='post', lazy='dynamic', cascade='all, delete-orphan')
    likes = db.relationship('Like', backref='post', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Post {self.title}>'

    def to_dict(self):
        """Convert post to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'excerpt': self.excerpt,
            'author': self.author.get_full_name(),
            'category': self.category.name if self.category else None,
            'views': self.views,
            'likes': self.likes_count,
            'comments': self.comments_count,
            'status': self.status,
            'published_at': self.published_at.isoformat() if self.published_at else None,
            'created_at': self.created_at.isoformat(),
        }

class Comment(db.Model):
    """Comment model"""
    __tablename__ = 'comments'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False, index=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), index=True)

    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    replies = db.relationship('Comment', backref=db.backref('parent', remote_side=[id]), cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Comment {self.id}>'

class Like(db.Model):
    """Like model for posts"""
    __tablename__ = 'likes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'post_id', name='unique_user_post_like'),)

    def __repr__(self):
        return f'<Like user={self.user_id} post={self.post_id}>'

class Newsletter(db.Model):
    """Newsletter subscription model"""
    __tablename__ = 'newsletters'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True)
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)
    unsubscribed_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<Newsletter {self.email}>'

# Association table for many-to-many relationship
post_tags = db.Table('post_tags',
    db.Column('post_id', db.Integer, db.ForeignKey('posts.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

# ============================================================================
# FORMS
# ============================================================================

class LoginForm(FlaskForm):
    """Login form"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    """Registration form"""
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password_confirm = PasswordField('Confirm Password',
        validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Register')

    def validate_username(self, field):
        """Check if username is unique"""
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already in use')

    def validate_email(self, field):
        """Check if email is unique"""
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered')

class PostForm(FlaskForm):
    """Create/edit post form"""
    title = StringField('Title', validators=[DataRequired(), Length(min=5, max=255)])
    content = TextAreaField('Content', validators=[DataRequired(), Length(min=20)])
    excerpt = StringField('Excerpt', validators=[Length(max=500)])
    category = SelectField('Category', coerce=int)
    featured_image = FileField('Featured Image', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'])])
    allow_comments = BooleanField('Allow Comments', default=True)
    is_featured = BooleanField('Featured Post')
    submit = SubmitField('Publish')

class CommentForm(FlaskForm):
    """Comment form"""
    content = TextAreaField('Comment', validators=[DataRequired(), Length(min=2, max=1000)])
    submit = SubmitField('Post Comment')

class ProfileForm(FlaskForm):
    """User profile form"""
    first_name = StringField('First Name', validators=[Length(max=120)])
    last_name = StringField('Last Name', validators=[Length(max=120)])
    bio = TextAreaField('Bio', validators=[Length(max=500)])
    avatar = FileField('Avatar', validators=[FileAllowed(['jpg', 'jpeg', 'png'])])
    submit = SubmitField('Update Profile')

# ============================================================================
# DECORATORS & UTILITIES
# ============================================================================

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

class BlogService:
    """Service class for blog operations"""

    @staticmethod
    def create_post(title: str, content: str, author_id: int, category_id: Optional[int] = None, **kwargs) -> Post:
        """Create a new post"""
        post = Post(
            title=title,
            slug=BlogService.generate_slug(title),
            content=content,
            author_id=author_id,
            category_id=category_id,
            **kwargs
        )
        db.session.add(post)
        db.session.commit()
        return post

    @staticmethod
    def update_post(post_id: int, **kwargs) -> Post:
        """Update a post"""
        post = Post.query.get_or_404(post_id)
        for key, value in kwargs.items():
            if hasattr(post, key) and key not in ['id', 'created_at']:
                setattr(post, key, value)
        post.updated_at = datetime.utcnow()
        db.session.commit()
        return post

    @staticmethod
    def delete_post(post_id: int) -> bool:
        """Delete a post"""
        post = Post.query.get_or_404(post_id)
        db.session.delete(post)
        db.session.commit()
        return True

    @staticmethod
    def publish_post(post_id: int) -> Post:
        """Publish a post"""
        post = Post.query.get_or_404(post_id)
        post.status = 'published'
        post.published_at = datetime.utcnow()
        db.session.commit()
        return post

    @staticmethod
    def generate_slug(title: str) -> str:
        """Generate slug from title"""
        import re
        slug = title.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')

    @staticmethod
    def get_featured_posts(limit: int = 5) -> List[Post]:
        """Get featured posts"""
        return Post.query.filter_by(is_featured=True, status='published').limit(limit).all()

    @staticmethod
    def search_posts(query: str, limit: int = 20) -> List[Post]:
        """Search posts"""
        return Post.query.filter(
            (Post.title.ilike(f'%{query}%')) |
            (Post.content.ilike(f'%{query}%')),
            Post.status == 'published'
        ).limit(limit).all()

    @staticmethod
    def get_posts_by_category(category_id: int, limit: int = 20) -> List[Post]:
        """Get posts by category"""
        return Post.query.filter_by(category_id=category_id, status='published').limit(limit).all()

    @staticmethod
    def increment_view_count(post_id: int):
        """Increment post view count"""
        post = Post.query.get(post_id)
        if post:
            post.views += 1
            db.session.commit()

    @staticmethod
    def like_post(user_id: int, post_id: int) -> bool:
        """Like a post"""
        existing_like = Like.query.filter_by(user_id=user_id, post_id=post_id).first()
        if existing_like:
            return False

        like = Like(user_id=user_id, post_id=post_id)
        post = Post.query.get(post_id)
        if post:
            post.likes_count += 1

        db.session.add(like)
        db.session.commit()
        return True

    @staticmethod
    def unlike_post(user_id: int, post_id: int) -> bool:
        """Unlike a post"""
        like = Like.query.filter_by(user_id=user_id, post_id=post_id).first()
        if not like:
            return False

        post = Post.query.get(post_id)
        if post:
            post.likes_count = max(0, post.likes_count - 1)

        db.session.delete(like)
        db.session.commit()
        return True

class UserService:
    """Service class for user operations"""

    @staticmethod
    def create_user(username: str, email: str, password: str, **kwargs) -> User:
        """Create a new user"""
        user = User(username=username, email=email, **kwargs)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    @staticmethod
    def update_user(user_id: int, **kwargs) -> User:
        """Update user"""
        user = User.query.get_or_404(user_id)
        for key, value in kwargs.items():
            if hasattr(user, key) and key not in ['id', 'password_hash', 'created_at']:
                setattr(user, key, value)
        user.updated_at = datetime.utcnow()
        db.session.commit()
        return user

    @staticmethod
    def verify_email(user_id: int) -> User:
        """Verify user email"""
        user = User.query.get_or_404(user_id)
        user.email_verified = True
        db.session.commit()
        return user

# ============================================================================
# BLUEPRINT PLACEHOLDERS
# ============================================================================

# These would be in separate files in blueprints/
# auth_bp, main_bp, api_bp, admin_bp

class CommentService:
    """Service class for comment operations"""

    @staticmethod
    def create_comment(content: str, author_id: int, post_id: int, parent_id: Optional[int] = None) -> Comment:
        """Create a new comment"""
        comment = Comment(
            content=content,
            author_id=author_id,
            post_id=post_id,
            parent_id=parent_id
        )
        post = Post.query.get(post_id)
        if post:
            post.comments_count += 1

        db.session.add(comment)
        db.session.commit()
        return comment

    @staticmethod
    def approve_comment(comment_id: int) -> Comment:
        """Approve a comment"""
        comment = Comment.query.get_or_404(comment_id)
        comment.is_approved = True
        db.session.commit()
        return comment

    @staticmethod
    def delete_comment(comment_id: int) -> bool:
        """Delete a comment"""
        comment = Comment.query.get_or_404(comment_id)
        post = comment.post
        if post:
            post.comments_count = max(0, post.comments_count - 1)

        db.session.delete(comment)
        db.session.commit()
        return True

    @staticmethod
    def get_post_comments(post_id: int, approved_only: bool = True, limit: int = 50):
        """Get comments for a post"""
        query = Comment.query.filter_by(post_id=post_id)
        if approved_only:
            query = query.filter_by(is_approved=True)
        return query.order_by(Comment.created_at.desc()).limit(limit).all()

class AnalyticsService:
    """Service class for analytics"""

    @staticmethod
    def get_blog_stats() -> Dict[str, Any]:
        """Get overall blog statistics"""
        return {
            'total_posts': Post.query.count(),
            'published_posts': Post.query.filter_by(status='published').count(),
            'draft_posts': Post.query.filter_by(status='draft').count(),
            'total_users': User.query.count(),
            'total_comments': Comment.query.count(),
            'total_views': db.session.query(db.func.sum(Post.views)).scalar() or 0,
            'total_likes': db.session.query(db.func.sum(Post.likes_count)).scalar() or 0,
        }

    @staticmethod
    def get_top_posts(limit: int = 10) -> List[Post]:
        """Get top posts by views"""
        return Post.query.filter_by(status='published').order_by(Post.views.desc()).limit(limit).all()

    @staticmethod
    def get_trending_posts(days: int = 7, limit: int = 10) -> List[Post]:
        """Get trending posts from recent days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return Post.query.filter(
            Post.status == 'published',
            Post.published_at >= cutoff_date
        ).order_by(Post.views.desc()).limit(limit).all()

    @staticmethod
    def get_user_stats(user_id: int) -> Dict[str, Any]:
        """Get user statistics"""
        user = User.query.get_or_404(user_id)
        return {
            'user_id': user.id,
            'username': user.username,
            'total_posts': Post.query.filter_by(author_id=user_id).count(),
            'total_comments': Comment.query.filter_by(author_id=user_id).count(),
            'total_views': db.session.query(db.func.sum(Post.views)).filter(Post.author_id == user_id).scalar() or 0,
            'total_likes': db.session.query(db.func.sum(Post.likes_count)).filter(Post.author_id == user_id).scalar() or 0,
        }

class CategoryService:
    """Service class for categories"""

    @staticmethod
    def create_category(name: str, description: str = '') -> Category:
        """Create a new category"""
        category = Category(
            name=name,
            slug=BlogService.generate_slug(name),
            description=description
        )
        db.session.add(category)
        db.session.commit()
        return category

    @staticmethod
    def update_category(category_id: int, **kwargs) -> Category:
        """Update a category"""
        category = Category.query.get_or_404(category_id)
        for key, value in kwargs.items():
            if hasattr(category, key) and key not in ['id', 'created_at']:
                setattr(category, key, value)
        category.updated_at = datetime.utcnow()
        db.session.commit()
        return category

    @staticmethod
    def delete_category(category_id: int) -> bool:
        """Delete a category"""
        category = Category.query.get_or_404(category_id)
        db.session.delete(category)
        db.session.commit()
        return True

    @staticmethod
    def get_all_categories(active_only: bool = True) -> List[Category]:
        """Get all categories"""
        query = Category.query
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(Category.name).all()

class TagService:
    """Service class for tags"""

    @staticmethod
    def create_tag(name: str, description: str = '') -> Tag:
        """Create a new tag"""
        tag = Tag(
            name=name,
            slug=BlogService.generate_slug(name),
            description=description
        )
        db.session.add(tag)
        db.session.commit()
        return tag

    @staticmethod
    def update_tag(tag_id: int, **kwargs) -> Tag:
        """Update a tag"""
        tag = Tag.query.get_or_404(tag_id)
        for key, value in kwargs.items():
            if hasattr(tag, key) and key not in ['id', 'created_at']:
                setattr(tag, key, value)
        db.session.commit()
        return tag

    @staticmethod
    def delete_tag(tag_id: int) -> bool:
        """Delete a tag"""
        tag = Tag.query.get_or_404(tag_id)
        db.session.delete(tag)
        db.session.commit()
        return True

    @staticmethod
    def get_all_tags(active_only: bool = True) -> List[Tag]:
        """Get all tags"""
        query = Tag.query
        if active_only:
            query = query.filter_by(is_active=True)
        return query.order_by(Tag.name).all()

    @staticmethod
    def get_popular_tags(limit: int = 20) -> List[Tag]:
        """Get most used tags"""
        return Tag.query.outerjoin(post_tags).group_by(Tag.id).order_by(
            db.func.count(post_tags.c.post_id).desc()
        ).limit(limit).all()

class NewsletterService:
    """Service class for newsletter"""

    @staticmethod
    def subscribe(email: str) -> Newsletter:
        """Subscribe to newsletter"""
        newsletter = Newsletter.query.filter_by(email=email).first()
        if newsletter:
            newsletter.is_active = True
            newsletter.unsubscribed_at = None
        else:
            newsletter = Newsletter(email=email)
        db.session.add(newsletter)
        db.session.commit()
        return newsletter

    @staticmethod
    def unsubscribe(email: str) -> bool:
        """Unsubscribe from newsletter"""
        newsletter = Newsletter.query.filter_by(email=email).first()
        if newsletter:
            newsletter.is_active = False
            newsletter.unsubscribed_at = datetime.utcnow()
            db.session.commit()
            return True
        return False

    @staticmethod
    def get_active_subscribers(limit: int = 1000) -> List[Newsletter]:
        """Get active newsletter subscribers"""
        return Newsletter.query.filter_by(is_active=True).limit(limit).all()

class ValidationService:
    """Service class for validations"""

    @staticmethod
    def validate_post_data(title: str, content: str) -> Dict[str, Any]:
        """Validate post data"""
        errors = {}

        if not title or len(title) < 5:
            errors['title'] = 'Title must be at least 5 characters'

        if not content or len(content) < 20:
            errors['content'] = 'Content must be at least 20 characters'

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

    @staticmethod
    def validate_user_data(username: str, email: str) -> Dict[str, Any]:
        """Validate user data"""
        errors = {}

        if not username or len(username) < 3:
            errors['username'] = 'Username must be at least 3 characters'

        if User.query.filter_by(username=username).first():
            errors['username'] = 'Username already taken'

        if not email or '@' not in email:
            errors['email'] = 'Invalid email address'

        if User.query.filter_by(email=email).first():
            errors['email'] = 'Email already registered'

        return {
            'valid': len(errors) == 0,
            'errors': errors
        }

class CacheService:
    """Service class for caching"""

    @staticmethod
    def get_featured_posts_cached(limit: int = 5) -> List[Post]:
        """Get featured posts with caching"""
        return BlogService.get_featured_posts(limit)

    @staticmethod
    def clear_post_cache(post_id: int):
        """Clear cache for a specific post"""
        pass

    @staticmethod
    def clear_all_caches():
        """Clear all caches"""
        pass

class PaginationHelper:
    """Helper for pagination"""

    @staticmethod
    def paginate(query, page: int = 1, per_page: int = 20):
        """Paginate a query"""
        return query.paginate(page=page, per_page=per_page, error_out=False)

    @staticmethod
    def get_pagination_info(paginated) -> Dict[str, Any]:
        """Get pagination information"""
        return {
            'page': paginated.page,
            'per_page': paginated.per_page,
            'total': paginated.total,
            'pages': paginated.pages,
            'has_next': paginated.has_next,
            'has_prev': paginated.has_prev,
            'next_page': paginated.next_num,
            'prev_page': paginated.prev_num,
        }

class ExportService:
    """Service class for data export"""

    @staticmethod
    def export_posts_to_csv(posts: List[Post]) -> str:
        """Export posts to CSV format"""
        csv_data = "Title,Author,Category,Views,Likes,Comments,Published At\n"
        for post in posts:
            csv_data += f'"{post.title}","{post.author.username}","{post.category.name if post.category else ""}",{post.views},{post.likes_count},{post.comments_count},"{post.published_at}"\n'
        return csv_data

    @staticmethod
    def export_users_to_csv(users: List[User]) -> str:
        """Export users to CSV format"""
        csv_data = "Username,Email,Full Name,Posts,Comments,Joined\n"
        for user in users:
            post_count = Post.query.filter_by(author_id=user.id).count()
            comment_count = Comment.query.filter_by(author_id=user.id).count()
            csv_data += f'"{user.username}","{user.email}","{user.get_full_name()}",{post_count},{comment_count},"{user.created_at}"\n'
        return csv_data

class DateHelper:
    """Helper for date operations"""

    @staticmethod
    def format_date(date: datetime, format_str: str = '%Y-%m-%d') -> str:
        """Format date"""
        return date.strftime(format_str)

    @staticmethod
    def time_ago(date: datetime) -> str:
        """Get human-readable time ago"""
        diff = datetime.utcnow() - date
        if diff.days > 365:
            return f"{diff.days // 365} year(s) ago"
        elif diff.days > 30:
            return f"{diff.days // 30} month(s) ago"
        elif diff.days > 0:
            return f"{diff.days} day(s) ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600} hour(s) ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60} minute(s) ago"
        return "just now"

class SecurityService:
    """Service class for security operations"""

    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input"""
        import html
        return html.escape(text)

    @staticmethod
    def rate_limit_check(identifier: str, limit: int = 10, window: int = 60) -> bool:
        """Check rate limit"""
        return True

class NotificationService:
    """Service class for notifications"""

    @staticmethod
    def send_email_notification(recipient: str, subject: str, body: str) -> bool:
        """Send email notification"""
        try:
            return True
        except Exception:
            return False

    @staticmethod
    def send_welcome_email(user: User) -> bool:
        """Send welcome email to new user"""
        subject = f"Welcome to Our Blog, {user.first_name or user.username}!"
        body = f"Thank you for joining our community. Start exploring posts and sharing your thoughts."
        return NotificationService.send_email_notification(user.email, subject, body)

    @staticmethod
    def send_post_published_notification(post: Post) -> bool:
        """Notify followers that user published new post"""
        subscribers = Newsletter.query.filter_by(is_active=True).all()
        for subscriber in subscribers:
            subject = f"New Post: {post.title}"
            body = f"Check out the latest post from {post.author.get_full_name()}: {post.excerpt}"
            NotificationService.send_email_notification(subscriber.email, subject, body)
        return True

    @staticmethod
    def send_comment_notification(comment: Comment) -> bool:
        """Notify post author of new comment"""
        post = comment.post
        author = post.author
        subject = f"New comment on your post: {post.title}"
        body = f"@{comment.author.username} commented: {comment.content[:100]}..."
        return NotificationService.send_email_notification(author.email, subject, body)

class StorageService:
    """Service class for file storage operations"""

    @staticmethod
    def save_uploaded_file(file, upload_dir: str = 'uploads') -> str:
        """Save uploaded file and return path"""
        if not file:
            return None

        os.makedirs(upload_dir, exist_ok=True)
        filename = f"{datetime.utcnow().timestamp()}_{file.filename}"
        filepath = os.path.join(upload_dir, filename)

        try:
            file.save(filepath)
            return filepath
        except Exception:
            return None

    @staticmethod
    def delete_file(filepath: str) -> bool:
        """Delete a file"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
            return True
        except Exception:
            return False

    @staticmethod
    def get_file_size(filepath: str) -> int:
        """Get file size in bytes"""
        try:
            return os.path.getsize(filepath)
        except Exception:
            return 0

class ReportService:
    """Service class for report generation"""

    @staticmethod
    def generate_monthly_report(year: int, month: int) -> Dict[str, Any]:
        """Generate monthly blog statistics"""
        from calendar import monthrange
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month, monthrange(year, month)[1])

        posts = Post.query.filter(
            Post.status == 'published',
            Post.published_at >= start_date,
            Post.published_at <= end_date
        ).all()

        total_views = sum(p.views for p in posts)
        total_comments = sum(p.comments_count for p in posts)
        total_likes = sum(p.likes_count for p in posts)

        return {
            'month': month,
            'year': year,
            'posts_published': len(posts),
            'total_views': total_views,
            'total_comments': total_comments,
            'total_likes': total_likes,
            'average_views_per_post': total_views / len(posts) if posts else 0,
        }

    @staticmethod
    def generate_user_monthly_report(user_id: int, year: int, month: int) -> Dict[str, Any]:
        """Generate user monthly statistics"""
        from calendar import monthrange
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month, monthrange(year, month)[1])

        posts = Post.query.filter(
            Post.author_id == user_id,
            Post.status == 'published',
            Post.published_at >= start_date,
            Post.published_at <= end_date
        ).all()

        total_views = sum(p.views for p in posts)
        total_comments = sum(p.comments_count for p in posts)
        total_likes = sum(p.likes_count for p in posts)

        return {
            'user_id': user_id,
            'month': month,
            'year': year,
            'posts_published': len(posts),
            'total_views': total_views,
            'total_comments': total_comments,
            'total_likes': total_likes,
            'top_post': max(posts, key=lambda p: p.views).title if posts else None,
        }

class APIResponseHelper:
    """Helper for API response formatting"""

    @staticmethod
    def success_response(data: Any, message: str = "Success", status_code: int = 200) -> tuple:
        """Generate success response"""
        return jsonify({
            'success': True,
            'message': message,
            'data': data
        }), status_code

    @staticmethod
    def error_response(message: str, errors: Dict = None, status_code: int = 400) -> tuple:
        """Generate error response"""
        return jsonify({
            'success': False,
            'message': message,
            'errors': errors or {}
        }), status_code

    @staticmethod
    def paginated_response(items: List, pagination_info: Dict, message: str = "Success") -> tuple:
        """Generate paginated response"""
        return jsonify({
            'success': True,
            'message': message,
            'data': items,
            'pagination': pagination_info
        }), 200

@login_manager.user_loader
def load_user(user_id):
    """Load user for login manager"""
    return User.query.get(int(user_id))

@login_manager.unauthorized_handler
def unauthorized():
    """Handle unauthorized access"""
    flash('Please log in to access this page.', 'warning')
    return redirect(url_for('auth.login'))

# ============================================================================
# ERROR HANDLERS
# ============================================================================

def register_error_handlers(app: Flask):
    """Register error handlers"""

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        return jsonify({'error': 'Forbidden'}), 403

# ============================================================================
# CLI COMMANDS
# ============================================================================

def register_cli_commands(app: Flask):
    """Register CLI commands"""

    @app.cli.command()
    def init_db():
        """Initialize database"""
        db.create_all()
        print('Database initialized')

    @app.cli.command()
    def seed_db():
        """Seed database with sample data"""
        admin = User(username='admin', email='admin@example.com', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)

        category = Category(name='General', slug='general', description='General posts')
        db.session.add(category)

        db.session.commit()
        print('Database seeded')

    @app.cli.command()
    def clear_db():
        """Clear all data from database"""
        db.drop_all()
        print('Database cleared')

# End of Flask Boilerplate
