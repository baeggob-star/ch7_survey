import streamlit as st
import pandas as pd
import numpy as np
import re


# --- 텍스트 전처리 헬퍼 함수 ---
def clean_grade(x):
    """학년 표기를 숫자로만 통일 (예: '1학년', '일학년' -> '1')"""
    if pd.isna(x): return x
    x = str(x)
    mapping = {'일': '1', '이': '2', '삼': '3', '사': '4'}
    for k, v in mapping.items():
        x = x.replace(k, v)
    match = re.search(r'\d+', x)
    return match.group() if match else x


def clean_college(x):
    """단과대학 이름을 규칙에 따라 분류"""
    if pd.isna(x): return x
    x = str(x)
    if '인문' in x: return '인문대학'
    if '사과' in x or '사회' in x: return '사회과학대학'
    if '경통' in x or '경제' in x: return '경제통상대학'
    if '경영' in x: return '경영대학'
    if '사범' in x: return '사범대학'
    return '기타'


def parse_time_to_minutes(x):
    """시간/분 텍스트를 분 단위 숫자로 변환 (예: 1시간 30분 -> 90)"""
    if pd.isna(x): return np.nan
    x = str(x).replace(" ", "")
    h_match = re.search(r'(\d+)시간', x)
    m_match = re.search(r'(\d+)분', x)

    if h_match or m_match:
        h = int(h_match.group(1)) if h_match else 0
        m = int(m_match.group(1)) if m_match else 0
        return h * 60 + m

    num_match = re.search(r'\d+', x)
    return int(num_match.group()) if num_match else np.nan


# --- 메인 페이지 로직 ---
def main():
    st.title("🛠️ 데이터 정제")

    # 사이드바 옵션 설정
    st.sidebar.header("정제 옵션 설정")
    outlier_threshold = st.sidebar.slider("AI 사용 시간 이상치 허용범위 (분)", 0, 1440, 300, step=10)
    missing_action = st.sidebar.radio("결측치(빈칸) 처리 방법", ["그대로 두기", "행삭제"])

    uploaded_file = st.file_uploader("구글 설문지 CSV 파일 업로드", type=['csv'])

    if uploaded_file:
        # 원본 데이터 로드
        try:
            raw_df = pd.read_csv(uploaded_file, dtype=str, encoding='utf-8-sig')
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            raw_df = pd.read_csv(uploaded_file, dtype=str, encoding='cp949')

        st.subheader("원본 데이터 미리보기")
        st.write(f"총 응답자 수(원본): **{len(raw_df)}명**")
        st.dataframe(raw_df)

        st.divider()
        st.subheader("데이터 정제 진행 중...")

        df = raw_df.copy()
        log_history = []

        # 1. 열 제목 변경
        new_cols = ["타임스탬프", "성별", "학년", "소속단과대학", "AI사용시간",
                    "활용", "신뢰", "학업정직성", "개인정보", "자율성", "정직성(역)", "서술형"]
        # 파일의 실제 열 개수만큼만 매칭하여 변경
        df.columns = new_cols[:len(df.columns)]
        log_history.append({"단계": "1. 열 제목 변경", "결과": "짧은 열 제목으로 일괄 변경 완료", "데이터 수": len(df)})

        # 2. 중복 데이터 제거
        subset_cols = [c for c in df.columns if c != '타임스탬프']
        df = df.drop_duplicates(subset=subset_cols, keep='first')
        log_history.append({"단계": "2. 중복 제거", "결과": f"{len(raw_df) - len(df)}건 중복 삭제됨", "데이터 수": len(df)})

        # 3. 학년 표기 통일
        if '학년' in df.columns:
            df['학년'] = df['학년'].apply(clean_grade)
            log_history.append({"단계": "3. 학년 통일", "결과": "숫자로만 표기 통일 완료", "데이터 수": len(df)})

        # 4. 단과대학 분류
        if '소속단과대학' in df.columns:
            df['소속단과대학'] = df['소속단과대학'].apply(clean_college)
            log_history.append({"단계": "4. 단과대학 통일", "결과": "키워드 기반 분류 완료", "데이터 수": len(df)})

        # 5. 이상치 처리 (시간 텍스트 변환 및 기준 초과 시 결측치 처리)
        if 'AI사용시간' in df.columns:
            df['AI사용시간'] = df['AI사용시간'].apply(parse_time_to_minutes)
            outlier_mask = df['AI사용시간'] > outlier_threshold
            df.loc[outlier_mask, 'AI사용시간'] = np.nan
            log_history.append(
                {"단계": "5. 이상치 처리", "결과": f"{outlier_threshold}분 초과 데이터 {outlier_mask.sum()}건 빈칸 처리", "데이터 수": len(df)})

        # 6. 결측치 확인 및 처리
        st.write("📊 **열별 결측치(빈칸) 수** (행삭제 전 기준)")
        st.dataframe(df.isna().sum().rename("결측치 개수").to_frame().T)

        if missing_action == "행삭제":
            before_drop = len(df)
            df = df.dropna()
            log_history.append({"단계": "6. 결측치 처리", "결과": f"빈칸 포함 {before_drop - len(df)}행 삭제 완료", "데이터 수": len(df)})
        else:
            log_history.append({"단계": "6. 결측치 처리", "결과": "빈칸 그대로 유지", "데이터 수": len(df)})

        # 7. 점수 계산 (역문항)
        if 'Q6' in df.columns:
            df['Q6'] = pd.to_numeric(df['Q6'], errors='coerce')
            df['Q6R'] = 6 - df['Q6']
            log_history.append({"단계": "7. 점수 산출", "결과": "Q6 역문항(Q6R) 계산 완료", "데이터 수": len(df)})

        # 세션 상태 저장
        st.session_state["clean_df"] = df

        st.divider()

        # --- 결과 표시 (카드 및 데이터프레임) ---
        st.subheader("최종 데이터 정제 결과")

        # 카드 형태로 지표 표시
        col1, col2, col3 = st.columns(3)
        col1.metric(label="📁 원본 데이터 수", value=f"{len(raw_df)}명")
        col2.metric(label="🗑️ 제거된 응답 수", value=f"{len(raw_df) - len(df)}명")
        col3.metric(label="✨ 최종 유효 응답 수", value=f"{len(df)}명")

        st.markdown("**📝 정제 기록 표**")
        st.dataframe(pd.DataFrame(log_history), use_container_width=True)

        st.markdown("**✨ 정제된 데이터**")
        st.dataframe(df, use_container_width=True)

        # CSV 다운로드
        csv_data = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 정제된 CSV 다운로드",
            data=csv_data,
            file_name="survey_cleaned.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    main()