from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
import os
from .models import db, User, Category, Receipt
from .ocr import parse_receipt
from .utils import download_image, auto_categorize, get_config, set_config
from sqlalchemy import func
from datetime import datetime, timedelta
import io
import csv
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = '/volume2/bookkeeper/bills'

db.init_app(app)

@app.before_first_request
def create_tables():
    db.create_all()

@app.route('/')
def index():
    return 'Flask NAS Receipt OCR 服务已启动！'

@app.route('/health')
def health():
    return {'status': 'ok'}

@app.route('/config', methods=['GET', 'POST'])
def config():
    config = get_config()
    if request.method == 'POST':
        webhook_url = request.form.get('webhook_url')
        token = request.form.get('token')
        config['webhook_url'] = webhook_url
        config['token'] = token
        set_config(config)
        flash('配置已保存', 'success')
    # 生成本服务的Webhook URL
    webhook_receive_url = request.url_root.rstrip('/') + url_for('webhook')
    return render_template('config.html', config=config, webhook_receive_url=webhook_receive_url)

def send_chat_message(user_id, text):
    config = get_config()
    CHAT_WEBHOOK_URL = config.get('webhook_url')
    TOKEN = config.get('token')
    if not CHAT_WEBHOOK_URL:
        print('未配置Chat Webhook URL')
        return
    payload = {
        'user_id': user_id,
        'text': text
    }
    headers = {'Authorization': f'Bearer {TOKEN}'} if TOKEN else {}
    try:
        requests.post(CHAT_WEBHOOK_URL, json=payload, headers=headers, timeout=5)
    except Exception as e:
        print('发送Chat消息失败:', e)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    # 假设 data 包含 user_id, user_name, image_url
    user_id = data.get('user_id')
    user_name = data.get('user_name')
    image_url = data.get('image_url')
    if not (user_id and image_url):
        return {'error': '参数缺失'}, 400
    # 用户入库
    user = User.query.filter_by(chat_id=user_id).first()
    if not user:
        user = User(chat_id=user_id, name=user_name)
        db.session.add(user)
        db.session.commit()
    # 下载图片
    save_dir = app.config['UPLOAD_FOLDER']
    image_path = download_image(image_url, save_dir)
    if not image_path:
        return {'error': '图片下载失败'}, 500
    # OCR 解析
    ocr_result = parse_receipt(image_path)
    # 自动分类
    cat_name = auto_categorize(ocr_result['details'])
    category = Category.query.filter_by(name=cat_name).first()
    if not category:
        category = Category(name=cat_name)
        db.session.add(category)
        db.session.commit()
    # 数据入库
    receipt = Receipt(
        user_id=user.id,
        category_id=category.id,
        merchant=ocr_result['merchant'],
        date=ocr_result['date'],
        amount=float(ocr_result['amount']) if ocr_result['amount'] else None,
        details=ocr_result['details'],
        image_path=image_path
    )
    db.session.add(receipt)
    db.session.commit()
    # 反馈解析结果到Chat
    feedback = f"小票解析结果：\n商家: {ocr_result['merchant']}\n日期: {ocr_result['date']}\n金额: {ocr_result['amount']}\n分类: {cat_name}\n商品明细: {ocr_result['details'][:100]}..."
    send_chat_message(user_id, feedback)
    return {'status': 'ok', 'receipt_id': receipt.id}

@app.route('/categories')
def categories():
    cats = Category.query.all()
    return render_template('categories.html', categories=cats)

@app.route('/categories/add', methods=['POST'])
def add_category():
    name = request.form.get('name')
    if name:
        if not Category.query.filter_by(name=name).first():
            db.session.add(Category(name=name))
            db.session.commit()
    return redirect(url_for('categories'))

@app.route('/categories/delete/<int:cat_id>')
def delete_category(cat_id):
    cat = Category.query.get(cat_id)
    if cat:
        db.session.delete(cat)
        db.session.commit()
    return redirect(url_for('categories'))

@app.route('/receipts')
def receipts():
    recs = Receipt.query.order_by(Receipt.created_at.desc()).all()
    return render_template('receipts.html', receipts=recs)

@app.route('/receipts/add', methods=['GET', 'POST'])
def add_receipt():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        category_id = request.form.get('category_id')
        merchant = request.form.get('merchant')
        date = request.form.get('date')
        amount = request.form.get('amount')
        details = request.form.get('details')
        receipt = Receipt(
            user_id=user_id,
            category_id=category_id,
            merchant=merchant,
            date=date,
            amount=float(amount) if amount else None,
            details=details
        )
        db.session.add(receipt)
        db.session.commit()
        return redirect(url_for('receipts'))
    users = User.query.all()
    categories = Category.query.all()
    return render_template('add_receipt.html', users=users, categories=categories)

@app.route('/stats')
def stats():
    return render_template('stats.html')

@app.route('/api/stats/monthly')
def api_stats_monthly():
    now = datetime.now()
    year_ago = now - timedelta(days=365)
    # 查询最近一年每月总金额
    results = db.session.query(
        func.strftime('%Y-%m', Receipt.date),
        func.sum(Receipt.amount)
    ).filter(
        Receipt.date >= year_ago.strftime('%Y-%m-%d')
    ).group_by(
        func.strftime('%Y-%m', Receipt.date)
    ).order_by(
        func.strftime('%Y-%m', Receipt.date)
    ).all()
    data = [{'month': r[0], 'total': r[1] or 0} for r in results]
    return jsonify(data)

@app.route('/api/stats/category/<month>')
def api_stats_category(month):
    # 查询指定月份各分类金额
    results = db.session.query(
        Category.name,
        func.sum(Receipt.amount)
    ).join(Category, Receipt.category_id == Category.id)
    results = results.filter(
        func.strftime('%Y-%m', Receipt.date) == month
    ).group_by(Category.name).all()
    data = [{'category': r[0], 'total': r[1] or 0} for r in results]
    return jsonify(data)

@app.route('/report')
def report():
    users = User.query.all()
    categories = Category.query.all()
    return render_template('report.html', users=users, categories=categories)

@app.route('/api/report/data')
def api_report_data():
    user_id = request.args.get('user_id', type=int)
    category_id = request.args.get('category_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    query = Receipt.query
    if user_id:
        query = query.filter(Receipt.user_id == user_id)
    if category_id:
        query = query.filter(Receipt.category_id == category_id)
    if date_from:
        query = query.filter(Receipt.date >= date_from)
    if date_to:
        query = query.filter(Receipt.date <= date_to)
    receipts = query.order_by(Receipt.date.desc()).all()
    # 汇总
    total = sum(r.amount or 0 for r in receipts)
    by_category = {}
    for r in receipts:
        cat = r.category.name if r.category else '未分类'
        by_category[cat] = by_category.get(cat, 0) + (r.amount or 0)
    data = [{
        'id': r.id,
        'user': r.user.name if r.user else '',
        'category': r.category.name if r.category else '',
        'merchant': r.merchant,
        'date': r.date,
        'amount': r.amount,
        'details': r.details,
        'created_at': r.created_at.strftime('%Y-%m-%d %H:%M')
    } for r in receipts]
    return jsonify({'data': data, 'total': total, 'by_category': by_category})

@app.route('/api/report/export')
def api_report_export():
    user_id = request.args.get('user_id', type=int)
    category_id = request.args.get('category_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    query = Receipt.query
    if user_id:
        query = query.filter(Receipt.user_id == user_id)
    if category_id:
        query = query.filter(Receipt.category_id == category_id)
    if date_from:
        query = query.filter(Receipt.date >= date_from)
    if date_to:
        query = query.filter(Receipt.date <= date_to)
    receipts = query.order_by(Receipt.date.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', '用户', '分类', '商家', '日期', '明细', '金额', '创建时间'])
    for r in receipts:
        writer.writerow([
            r.id,
            r.user.name if r.user else '',
            r.category.name if r.category else '',
            r.merchant,
            r.date,
            r.details,
            r.amount,
            r.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    output.seek(0)
    return send_file(io.BytesIO(output.read().encode('utf-8-sig')),
                     mimetype='text/csv',
                     as_attachment=True,
                     download_name='report.csv')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9090) 