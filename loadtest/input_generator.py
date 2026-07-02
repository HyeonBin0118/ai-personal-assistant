import random


def generate_random_input() -> str:
    """
    실제 사용자가 AI 비서에게 입력할 법한 자연스러운 문장을 랜덤 생성.
    완전 일치 캐시 히트율을 현실적(5~15%)으로 만들기 위해
    같은 의미도 다양한 표현으로 생성.
    """
    category = random.choice(["expense", "expense", "schedule", "todo"])
    # 지출이 실생활에서 제일 자주 기록하니까 가중치 2배

    if category == "expense":
        return _generate_expense()
    elif category == "schedule":
        return _generate_schedule()
    else:
        return _generate_todo()


# ── 지출 ──────────────────────────────────────────────────────────────────────

def _generate_expense() -> str:
    subcategory = random.choice([
        "cafe", "meal", "transport", "grocery", "delivery",
        "shopping", "health", "entertainment", "etc"
    ])

    if subcategory == "cafe":
        items = ["커피", "아메리카노", "아아", "뜨아", "라떼", "카페라떼",
                 "바닐라라떼", "콜드브루", "드립커피", "녹차라떼", "카라멜마키아토",
                 "에스프레소", "플랫화이트", "디카페인"]
        brands = ["스타벅스", "이디야", "메가커피", "컴포즈", "투썸", "할리스",
                  "커피빈", "폴바셋", "블루보틀", "맥카페", "공차", "빽다방"]
        prices = [2000, 2500, 3000, 3500, 4000, 4500, 5000, 5500, 6000, 6500, 7000]
        times = ["아침에", "점심에", "오후에", "퇴근하면서", "출근하면서",
                 "회의 전에", "잠깐", "오늘", "아까", "방금"]
        places = random.choice(brands + ["카페에서", "근처 카페에서", "회사 앞 카페에서"])
        templates = [
            f"{random.choice(times)} {random.choice(items)} {random.choice(prices)}원",
            f"{places} {random.choice(items)} 한 잔 {random.choice(prices)}원",
            f"{random.choice(items)} {random.choice(prices)}원",
            f"{random.choice(times)} {places} {random.choice(prices)}원",
            f"오늘 {places} {random.choice(items)} 마셨어 {random.choice(prices)}원",
            f"{random.choice(times)} 커피 한 잔 했어 {random.choice(prices)}원",
        ]

    elif subcategory == "meal":
        foods = ["점심", "저녁", "아침", "밥", "국밥", "설렁탕", "삼겹살", "냉면",
                 "짜장면", "짬뽕", "라멘", "파스타", "스시", "초밥", "샐러드",
                 "치킨", "피자", "햄버거", "샌드위치", "분식", "떡볶이", "순대",
                 "마라탕", "쌀국수", "덮밥", "카레", "도시락", "편의점 밥"]
        prices = [5000, 6000, 7000, 7500, 8000, 8500, 9000, 9500, 10000,
                  11000, 12000, 13000, 14000, 15000, 18000, 20000, 25000]
        with_who = ["", "혼자", "친구랑", "팀원이랑", "선배랑", "동료랑"]
        times = ["오늘 점심", "오늘 저녁", "점심에", "저녁에", "아까",
                 "오늘", "어제 저녁", "어제 점심"]
        templates = [
            f"{random.choice(times)} {random.choice(with_who)} {random.choice(foods)} {random.choice(prices)}원",
            f"{random.choice(foods)} 먹었어 {random.choice(prices)}원",
            f"{random.choice(times)} {random.choice(foods)} 먹었는데 {random.choice(prices)}원 나왔어",
            f"{random.choice(with_who)} {random.choice(foods)} 먹었어 {random.choice(prices)}원",
            f"{random.choice(foods)} {random.choice(prices)}원",
            f"오늘 {random.choice(foods)} {random.choice(prices)}원 씀",
        ]

    elif subcategory == "transport":
        transports = ["택시", "카카오택시", "지하철", "버스", "KTX", "기차",
                      "고속버스", "시외버스", "따릉이", "킥보드"]
        prices = [1200, 1350, 1500, 2700, 3500, 5000, 6000, 7000, 8000,
                  9000, 10000, 12000, 15000, 18000, 25000, 35000, 53000]
        routes = ["", "집까지", "회사까지", "강남까지", "홍대까지", "서울역까지",
                  "출근", "퇴근", "왕복"]
        templates = [
            f"{random.choice(transports)} {random.choice(routes)} {random.choice(prices)}원",
            f"오늘 {random.choice(transports)} 탔어 {random.choice(prices)}원",
            f"{random.choice(transports)} {random.choice(prices)}원",
            f"교통비 {random.choice(transports)} {random.choice(prices)}원",
        ]

    elif subcategory == "grocery":
        places = ["마트", "이마트", "홈플러스", "코스트코", "편의점", "GS25",
                  "CU", "세븐일레븐", "올리브영", "다이소", "농협"]
        prices = [3000, 5000, 8000, 10000, 15000, 20000, 25000, 30000,
                  35000, 45000, 55000, 65000, 78000, 100000]
        templates = [
            f"{random.choice(places)} {random.choice(prices)}원",
            f"오늘 {random.choice(places)} 들렀어 {random.choice(prices)}원",
            f"장봤어 {random.choice(prices)}원",
            f"{random.choice(places)}에서 {random.choice(prices)}원 썼어",
            f"마트 장보기 {random.choice(prices)}원",
        ]

    elif subcategory == "delivery":
        apps = ["배달의민족", "배민", "쿠팡이츠", "요기요"]
        foods = ["치킨", "피자", "족발", "보쌈", "중국집", "분식", "버거",
                 "초밥", "마라탕", "떡볶이", "야식"]
        prices = [15000, 18000, 20000, 22000, 25000, 28000, 30000, 35000]
        templates = [
            f"{random.choice(apps)} {random.choice(foods)} 시켰어 {random.choice(prices)}원",
            f"배달 {random.choice(foods)} {random.choice(prices)}원",
            f"오늘 야식 {random.choice(foods)} 시켰어 {random.choice(prices)}원",
            f"{random.choice(foods)} 배달 {random.choice(prices)}원",
        ]

    elif subcategory == "shopping":
        items = ["옷", "신발", "가방", "화장품", "스킨케어", "책", "운동용품",
                 "생활용품", "전자기기", "이어폰", "충전기"]
        places = ["쿠팡", "네이버쇼핑", "무신사", "지그재그", "올리브영", "아이허브"]
        prices = [10000, 15000, 20000, 25000, 35000, 45000, 55000, 75000, 89000, 120000]
        templates = [
            f"{random.choice(items)} 샀어 {random.choice(prices)}원",
            f"{random.choice(places)}에서 {random.choice(items)} {random.choice(prices)}원",
            f"온라인 쇼핑 {random.choice(prices)}원",
            f"{random.choice(items)} 구매 {random.choice(prices)}원",
        ]

    elif subcategory == "health":
        places = ["병원", "치과", "피부과", "안과", "한의원", "정형외과", "내과",
                  "약국", "헬스장", "필라테스", "요가"]
        prices = [5000, 8000, 10000, 15000, 20000, 25000, 35000, 45000,
                  55000, 60000, 80000, 85000, 120000]
        templates = [
            f"{random.choice(places)} 다녀왔어 {random.choice(prices)}원",
            f"오늘 {random.choice(places)} {random.choice(prices)}원",
            f"{random.choice(places)} 비용 {random.choice(prices)}원",
        ]

    elif subcategory == "entertainment":
        items = ["영화", "공연", "전시회", "콘서트", "노래방", "볼링", "방탈출"]
        prices = [10000, 12000, 14000, 15000, 20000, 25000, 35000, 55000, 110000]
        templates = [
            f"{random.choice(items)} 봤어 {random.choice(prices)}원",
            f"오늘 {random.choice(items)} {random.choice(prices)}원",
            f"{random.choice(items)} 티켓 {random.choice(prices)}원",
        ]

    else:  # etc
        items = ["미용실", "헤어컷", "세탁소", "주차비", "공과금", "넷플릭스",
                 "유튜브 프리미엄", "핸드폰 요금", "인터넷 요금"]
        prices = [5000, 8000, 10000, 14000, 15000, 35000, 45000, 55000, 85000]
        templates = [
            f"{random.choice(items)} {random.choice(prices)}원",
            f"오늘 {random.choice(items)} 냈어 {random.choice(prices)}원",
            f"{random.choice(items)} 결제 {random.choice(prices)}원",
        ]

    return random.choice(templates)


# ── 일정 ──────────────────────────────────────────────────────────────────────

def _generate_schedule() -> str:
    days = ["오늘", "내일", "모레", "이번 주 월요일", "이번 주 화요일",
            "이번 주 수요일", "이번 주 목요일", "이번 주 금요일",
            "이번 주 토요일", "이번 주 일요일",
            "다음 주 월요일", "다음 주 화요일", "다음 주 수요일",
            "다음 주 목요일", "다음 주 금요일", "다음 주 토요일"]
    times = ["오전 9시", "오전 10시", "오전 10시 30분", "오전 11시",
             "오후 12시", "오후 1시", "오후 1시 30분", "오후 2시",
             "오후 3시", "오후 4시", "오후 5시", "오후 6시",
             "오후 7시", "오후 7시 30분", "저녁 8시"]
    events = ["치과", "피부과", "병원", "한의원", "안과", "정형외과",
              "팀 미팅", "회의", "화상 회의", "클라이언트 미팅",
              "면접", "스탠드업", "1on1", "점심 미팅", "팀 회식",
              "친구 만나기", "선배 만남", "동창 모임", "소개팅",
              "헬스장", "필라테스", "요가", "수영",
              "은행 방문", "주민센터", "자동차 검사", "택배 수령"]
    notify_options = ["", "30분 전에 알려줘", "1시간 전에 알려줘",
                      "10분 전에 알림", "2시간 전에 알려줘", "15분 전에 알림"]

    day = random.choice(days)
    time = random.choice(times)
    event = random.choice(events)
    notify = random.choice(notify_options)

    templates = [
        f"{day} {time} {event}" + (f" {notify}" if notify else ""),
        f"{event} {day} {time}" + (f" {notify}" if notify else ""),
        f"{day} {event} {time}에 있어" + (f" {notify}" if notify else ""),
        f"{event} 일정 {day} {time}" + (f" {notify}" if notify else ""),
        f"{day} {time}에 {event} 예약돼있어" + (f" {notify}" if notify else ""),
    ]

    return random.choice(templates)


# ── 투두 ──────────────────────────────────────────────────────────────────────

def _generate_todo() -> str:
    tasks = [
        # 업무
        "보고서 작성", "이메일 답장", "회의록 정리", "코드 리뷰",
        "기획서 작성", "PPT 만들기", "데이터 분석", "제안서 제출",
        "PR 올리기", "배포 작업", "버그 수정", "슬랙 확인",
        # 생활
        "집 청소", "빨래하기", "설거지", "쓰레기 버리기", "재활용",
        "장보기", "요리하기", "냉장고 정리", "화장실 청소", "침구 세탁",
        # 개인
        "운동하기", "책 읽기", "영어 공부", "일기 쓰기", "독서",
        "명상", "스트레칭", "물 2리터 마시기", "비타민 챙기기",
        # 연락
        "엄마한테 전화", "친구한테 연락", "답장 보내기", "안부 연락",
        "생일 축하 메시지",
        # 행정
        "공과금 납부", "카드 실적 확인", "보험료 납부", "세금 처리",
        "자격증 등록", "여권 갱신", "운전면허 갱신",
        # 학습
        "파이썬 공부", "알고리즘 문제 풀기", "강의 듣기", "과제 제출",
        "포트폴리오 업데이트", "이력서 수정",
    ]

    deadlines = ["", "오늘", "내일까지", "이번 주 안에", "오늘 저녁에",
                 "퇴근 전에", "자기 전에", "오늘 오전에"]
    suffixes = ["", " 해야 해", " 잊지 말기", " 해야지", " 하기", " 처리하기"]

    task = random.choice(tasks)
    deadline = random.choice(deadlines)
    suffix = random.choice(suffixes)

    templates = [
        f"{deadline} {task}{suffix}".strip(),
        f"{task}{suffix}",
        f"{deadline} {task} 꼭 해야 해".strip(),
        f"{task} {deadline} 잊지 말기".strip(),
    ]

    return random.choice(templates).strip()