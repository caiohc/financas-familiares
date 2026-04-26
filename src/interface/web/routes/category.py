import uuid
from flask import Blueprint, render_template, request, redirect, url_for, current_app

category_bp = Blueprint('category', __name__, url_prefix='/categories')

@category_bp.route('/')
def index():
    service = current_app.config['CATEGORY_SERVICE']
    categories = service.list_all()
    # It might be nice to separate incomes from expenses in the view or list them together
    return render_template('category/index.html', categories=categories)

@category_bp.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        name = request.form.get('name')
        transaction_type_str = request.form.get('type')
        if name and transaction_type_str in ["INCOME", "EXPENSE"]:
            service = current_app.config['CATEGORY_SERVICE']
            service.create_category(name=name, transaction_type_str=transaction_type_str)
            return redirect(url_for('category.index'))
    return render_template('category/form.html', category=None)

@category_bp.route('/<uuid:category_id>/update', methods=['GET', 'POST'])
def update(category_id):
    service = current_app.config['CATEGORY_SERVICE']
    category_obj = service.get_category(category_id)
    
    if not category_obj:
        return redirect(url_for('category.index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        transaction_type_str = request.form.get('type')
        if name and transaction_type_str in ["INCOME", "EXPENSE"]:
            service.update_category(category_id, name, transaction_type_str)
            return redirect(url_for('category.index'))
            
    return render_template('category/form.html', category=category_obj)

@category_bp.route('/<uuid:category_id>/delete', methods=['POST'])
def delete(category_id):
    service = current_app.config['CATEGORY_SERVICE']
    service.delete_category(category_id)
    return redirect(url_for('category.index'))
