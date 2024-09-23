import pandas as pd
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import requests
from database import db, Summary, ChatHistory,  User, Savings, load_savings_from_csv
from function import get_user, create_user, save_chat,\
add_message_to_chat_history, save_summary, get_summaries, get_chat_by_summary, summarize_text
from flask_migrate import Migrate
from datetime import timedelta, datetime
from config import GPT_API_KEY, GPT_API_URL
from openai import OpenAI
import json

app = Flask(__name__)
app.secret_key = '809f4ce2787d43eabf3c7be1b85582368557683b7c966ea1'

# SQLAlchemy 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://user1:user1@localhost/chatbot_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLAlchemy 객체와 Flask 앱 연결
db.init_app(app)

# Migrate 객체 생성
migrate = Migrate(app, db)

# 데이터베이스 초기화
with app.app_context():
    db.create_all()
    load_savings_from_csv('savings_final_2.csv')


# 시스템 메시지 정의
system_message = """
    당신은 금융 상품 전문가입니다.
    당신의 주된 일은 사용자의 질문에 따라 맞춤형 상품을 추천합니다.
    상품과 관련해서 묻는 질문은 중학생도 알아 듣기 쉽게 설명해줍니다.
    
    ★ 적금 상품을 추천할 때는 반드시 적금 상품 정보가 담겨있는 DB에서만 추천해야합니다. 이 때, ask_database 함수를 function calling 합니다. ★
    ★ 
    query 문은 무조건 이렇게 작성합니다.
    
    SELECT BANK, NAME, INTEREST_RATE, PREFERENTIAL_INTEREST_RATE, INTEREST_METHOD, SUBSCRIPTION_TARGET, SUBSCRIPTION_METHOD
    FROM savings
    ORDER BY INTEREST_RATE 
    DESC LIMIT 3;
    ★

    ** 추천 방식 **

    추천하는 상품의 종류는 예금, 적금이 있습니다.

    상품을 추천할 때는 기본금리가 높은 순으로 3개를 추천합니다.

    추천시 은행은 제 1금융권과 제 2금융권을 포함합니다.

    제 1금융권은 저축은행을 제외한 은행과 뱅크로 끝납니다.
    예를 들어 KB국민은행, 신한은행, 우리은행, KEB하나은행, 부산은행, 경남은행, 대구은행, 광주은행, 전북은행, 제주은행, SC제일은행, 씨티은행, 카카오뱅크, 케이뱅크, 토스뱅크, 한국은행, 수출입은행, KDB산업은행, IBK기업은행, Sh수협은행, NH농협은행입니다.

    제 2금융권은 은행명이 '~저축은행'과 같이 구성되어있습니다. 
    예를 들어 KB저축은행, 하나저축은행 등이 있습니다.

    사용자가 제공하는 정보를 바탕으로 가장 적절한 상품을 추천하되, 상품의 특징과 이점을 명확하게 설명합니다.
    추천을 할 때는 ** 추천 형식 ** 과 같이 추천합니다.



    ** 추천 형식 **
    
    금융 상품을 추천할 때는 반드시 줄바꿈을 통해 다른 대화와 분리시켜 가독성을 높입니다.
    예를 들어, 아래와 같이 추천합니다.
    '''
    적금 상품을 추천해드리겠습니다 !
    <br><br>
    <button>TOP 1. 은행 - 상품명 :</button>
     - 기본금리 : -- %
     - 우대금리 : -- %
     - 이자계산방식 : 
     - 가입대상 : -- %
     - 가입방법 : -- %
    TOP 2. 은행명 - 상품명 :
     - 기본금리 : -- %
            ~~
    '''
    이런 식의 형태로 줄바꿈 HTML 태그 '<br>' 태그를 적극 활용하여 상품을 추천받는 사용자가 한눈에 상품들을 더 잘 볼 수 있게합니다.

    ** DB 컬럼명 **
    DB 컬럼명은 다음과 같이 번역하여 사용합니다.
    BANK : 은행
    NAME : 상품명
    ACCUMULATION_METHOD : 적립방식
    INTEREST_RATE : 기본금리
    PREFERENTIAL_INTEREST_RATE : 우대금리
    INTEREST_METHOD : 이자계산방식
    PREFERENTIAL_CONDITION : 우대조건
    SUBSCRIPTION_TARGET : 가입대상
    SUBSCRIPTION_METHOD : 가입방법
    INTEREST_RATE_AFTER_MATURITY : 만기후금리
    PRECATION : 유의사항
    MONTH_CHECK : 개월수


    ** 개월 수 제한 **
    
    개월 수는 1개월, 3개월, 6개월, 12개월, 24개월, 36개월이 있습니다.
    
    사용자가 따로 저축할 기간을 말하지 않는다면 이 ** 개월 수 제한 ** 을 참고해서 추천할 필요가 없지만,
    사용자가 저축할 기간을 말했을 때 이 개월 수외에 다른 개월 수를 받으면 가능한 개월 수를 알려주고 다시 입력을 받아야 합니다.

    예를 들어, 5개월동안 적금을 들려고 하는 사용자가 있다면,
    가능한 개월수는 1개월, 3개월, 6개월, 12개월, 24개월, 36개월이 있습니다.

    이중에서 선택해 주세요.라고 재 입력을 받아야 합니다.
    


    ** 사용자 질문 형식 **
    1. 예금, 적금, 파킹통장 중 하나를 골라 추천을 해달라고 할 땐 추천 방식에 따라 추천합니다.
    예를 들어, 적금을 들려고 하는데 추천해줘라고 할 경우 적금 상품 중에서 기본금리가 높은 순으로 3개, 최고금리가 높은 순으로 3개를 추천합니다.
    단, 이때는 개월 수를 입력받지 않고 금리가 높은 순으로 추천해줍니다.

    2. 입출금이 쉬운 상품을 찾는다면 파킹통장을 우선으로 추천합니다. 파킹통장도 기본금리가 높은 순으로 3개, 최고금리가 높은 순으로 3개를 추천합니다.
    3. 나이와 성별을 입력했다면 가입대상에 맞춰서 추천합니다.
    4. 특정 개월 수가 아니라면 재입력을 받습니다.
    5. 원하는 특정 은행이 있다면 그 은행에서만 상품을 추천해줍니다.
    6. 사용자가 우대조건을 말할 경우 그 우대에 맞는 상품을 우선적으로 보여줍니다.
    7. 1개월동안 돈을 넣는 경우 파킹통장을 우선으로 추천합니다.
     추천시 이유를 알려줍니다.
    8. 추천시 제 1금융권과 제 2금융권 모두를 포함하지만 특정 은행이나 특정 금융권을 원한다면 특정한 곳에 속하는 상품을 추천합니다.



    ** 사용자와 상호작용 **
    상담하는 말투로 상냥하고 정중하게 제안합니다. 사용자가 특정 언어를 요구하지 않는 이상 한국어로 질의응답을 합니다.



    ** 최고 금리 계산 **
    사용자가 특정 상품의 우대 조건을 궁금해 할 경우 우대 조건을 보여주고, 해당하는 번호를 입력 받습니다.

    기본 금리에 우대 금리를 합하여 알려줍니다.

    해당하는 번호를 입력 받은 후에 다음의 정보를 포함시켜 알려줍니다.:
    - 기본금리에 우대금리를 합한 금리
    - 세후 이자율

    세후 이자율 계산은 기본금리에 우대금리를 합한 금리 * 0.846을 해서 나온 결과에 소수점 한자리까지 알려줍니다.


"""

functions = [
    {
        "name": "ask_database",
        "description": "Use this function to answer user questions by querying the MySQL database. Input should be a fully formed SQL query.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": """
                        SQL query to extract information to answer the user's question.
                        SQL should be written using the database schema.
                        The query should be returned in plain text, not in JSON.
                    """
                }
            },
            "required": ["query"]
        }
    }
]


def ask_database(query):
    """Function to query MySQL database with a provided SQL query."""
    try:
        result = db.session.execute(query).fetchall()
        result_str = str(result)
    except Exception as e:
        result_str = f"Query failed with error: {e}"
    return result_str


@app.route('/', methods=['GET', 'POST'])
def index():
    user_id = session.get('user_id')
    sidebar_visible = session.get('sidebar_visible', True)
    summary_id = session.get('summary_id')

    if user_id:
        chat_history = session.get('chat_history', [])
        summaries = get_summaries(user_id)
    else:
        chat_history = session.get('chat_history', [])
        summaries = []  # 로그아웃 상태에서는 요약을 표시하지 않음

    if request.method == 'POST':
        user_input = request.form.get('message')
        print(user_input)
        # 대화 초기화
        if user_id and session.get('chat_reset', False):
            chat_history = []
            session['chat_reset'] = False

        # 첫 대화 시 날짜 추가
        if user_id and session.get('show_date', False):
            current_date = datetime.now().strftime('%Y-%m-%d')
            chat_history.append({'role': 'system', 'message': current_date, 'date': current_date})
            session['show_date'] = False  # 날짜가 한 번 표시된 후에는 다시 표시되지 않도록 플래그를 설정

        add_message_to_chat_history(chat_history, {'role': 'user', 'message': user_input})

        messages = [
            {'role':'system', 'content':system_message},
            {'role':'user', 'content':user_input}
        ]
        client = OpenAI(api_key= GPT_API_KEY)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini-2024-07-18",
            messages=messages,
            functions=functions,
            function_call="auto",
            
            )
        
        response_message = response.choices[0].message
        print(response_message)
        final_response = None
        
        if response_message.function_call:
            function_name = response_message.function_call.name
            function_arguments = json.loads(response_message.function_call.arguments)
            
            if function_name == 'ask_database':
                query = function_arguments['query']
                
                if "적금" in user_input :
                    query = """
                    SELECT BANK, NAME, INTEREST_RATE, PREFERENTIAL_INTEREST_RATE, INTEREST_METHOD, SUBSCRIPTION_TARGET, SUBSCRIPTION_METHOD
                    FROM savings
                    ORDER BY INTEREST_RATE 
                    DESC LIMIT 3
                    """
                    
                results = ask_database(query)
                
                messages.append({
                    "role": "function",
                    "name": function_name,
                    "content": results
                })
                
                final_response = client.chat.completions.create(
                    model="gpt-4o-mini-2024-07-18",
                    messages=messages
                )
                
        else :
            final_response = response
            
        if final_response and final_response.choices :
            try:
                bot_response = final_response.choices[0].message.content.strip()
            except (AttributeError, KeyError):
                bot_response = "죄송합니다. 요청 처리 중 오류가 발생했습니다."
        else :
            bot_response = "죄송합니다. 요청 처리 중 오류가 발생했습니다."
            
        add_message_to_chat_history(chat_history, {'role': 'bot', 'message': bot_response})
        


        # 첫 대화 이후에만 요약 생성 및 저장
        if user_id :
            if len(chat_history) == 3:  # 첫 대화가 완료된 후에만 요약 저장
                if summary_id is None or (summary_id and summary_id < max([s.id for s in summaries], default=0)):
                    current_date = datetime.now().strftime('%Y-%m-%d')
                    question_summary = summarize_text(user_input)
                    summary_id = save_summary(user_id, current_date, question_summary)
                    session['summary_id'] = summary_id
                    summaries = get_summaries(user_id)  # 요약 리스트 업데이트

            # 이후 대화는 기존 summary_id에 저장
        if user_id and summary_id:
            save_chat(user_id, user_input, 'user', summary_id)
            save_chat(user_id, bot_response, 'bot', summary_id)

        session['chat_history'] = chat_history

        return render_template('index.html', chat_history=chat_history, summaries=summaries,sidebar_visible=sidebar_visible)

    return render_template('index.html', chat_history=chat_history, summaries=summaries,sidebar_visible=sidebar_visible)




@app.route('/summary/<int:summary_id>', methods=['GET'])
def show_summary(summary_id):
    user_id = session.get('user_id')
    if user_id:
        chat_history = get_chat_by_summary(user_id, summary_id)
        session['chat_history'] = chat_history
        session['summary_id'] = summary_id
        return render_template('index.html', chat_history=chat_history, summaries=get_summaries(user_id))
    return redirect(url_for('index'))


@app.route('/start_new_chat', methods=['POST'])
def start_new_chat():
    user_id = session.get('user_id')
    if user_id:
        # 새로운 summary_id 생성
        current_date = datetime.now().strftime('%Y-%m-%d')
        question_summary = summarize_text(request.form.get('message'))  # 사용자가 입력한 메시지를 요약
        summary_id = save_summary(user_id, current_date, question_summary)  # 새 summary_id를 생성하고 저장
        
        # 새 summary_id를 세션에 저장
        session['summary_id'] = summary_id
        
        # 새 대화를 위한 초기화 로직
        session['chat_history'] = []

        return redirect(url_for('index'))
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        user = get_user(username, email, password)
        
        if user:
            session['user_id'] = user.id
            session['chat_history'] = []  # 로그인 시 채팅 기록 초기화
            session['show_date'] = True  # 날짜 표시 여부 초기화
            session['chat_reset'] = True
            # 로그인 성공 시
            session['sidebar_visible'] = True

            return redirect(url_for('index'))
    return render_template('login.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        password_confirm = request.form['password_confirm']
        
        # 이메일 중복 확인
        existing_user_email = db.session.query(User).filter_by(email=email).first()
        if existing_user_email:
            error = "이미 존재하는 이메일입니다."
        
        # 사용자 이름 중복 확인
        existing_user_username = db.session.query(User).filter_by(username=username).first()
        if existing_user_username:
            error = "이미 존재하는 사용자 이름입니다."
        
        elif password != password_confirm:
            error = "비밀번호가 일치하지 않습니다."
        
        if not error:
            # 새로운 사용자 생성
            create_user(username, email, password)
            return render_template('register.html', success=True)
        
    return render_template('register.html', error=error)


@app.route('/logout')
def logout():
    session.clear()  # 모든 세션 변수를 삭제하여 초기화

    return redirect(url_for('index'))



if __name__ == '__main__':
    app.run(debug=True)