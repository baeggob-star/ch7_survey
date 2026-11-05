import streamlit as st
import pandas as pd
import numpy as np


def get_data():
    # 세션 상태에서 정제된 데이터 및 원본 데이터 확인
    if "clean_df" in st.session_state:
        clean_df = st.session_state["clean_df"]
        # 프롬프트 1, 3의 환경을 고려하여 raw_df가 세션에 있다면 함께 불러오기
        raw_df = st.session_state.get("raw_df", None)
        return clean_df, raw_df
    else:
        # 세션에 데이터가 없을 경우 안내 문구 출력 및 파일 업로더 제공
        st.warning("정제된 데이터가 없습니다. 데이터 정제 페이지를 먼저 실행하거나 CSV를 업로드하세요.")
        uploaded_file = st.file_uploader("정제된 데이터(CSV) 업로드", type=['csv'])
        if uploaded_file:
            clean_df = pd.read_csv(uploaded_file)
            return clean_df, None
        return None, None


def calculate_derived_scores(df):
    # 활용점수와 윤리의식 점수가 데이터에 없을 경우를 대비해 계산
    df = df.copy()

    # Q1~Q6R 열을 숫자로 변환
    q_cols = ['Q1', 'Q2', 'Q3', 'Q4', 'Q5', 'Q6R']
    for col in q_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # AI활용점수 (Q1, Q2 평균)
    if 'AI활용점수' not in df.columns and 'Q1' in df.columns and 'Q2' in df.columns:
        df['AI활용점수'] = df[['Q1', 'Q2']].mean(axis=1)

    # AI윤리의식 (Q3, Q4, Q5, Q6R 평균)
    if 'AI윤리의식' not in df.columns and all(c in df.columns for c in ['Q3', 'Q4', 'Q5', 'Q6R']):
        df['AI윤리의식'] = df[['Q3', 'Q4', 'Q5', 'Q6R']].mean(axis=1)

    return df


def show_summary_metrics(df):
    # 상단 요약 지표 표시 (유효 응답 수, 사용 시간 평균, 윤리 의식 평균)
    st.subheader("요약 지표")
    col1, col2, col3 = st.columns(3)

    col1.metric("유효 응답 수", f"{len(df)}명")

    if 'AI사용시간' in df.columns:
        avg_time = pd.to_numeric(df['AI사용시간'], errors='coerce').mean()
        col2.metric("평균 AI 사용 시간", f"{avg_time:.1f}분")

    if 'AI윤리의식' in df.columns:
        avg_ethics = df['AI윤리의식'].mean()
        col3.metric("AI윤리의식 평균", f"{avg_ethics:.2f}점")


def show_before_after_comparison(clean_df, raw_df):
    # 단과대학별 응답자 수를 나란히 비교하여 가로 막대 그래프로 표시
    st.subheader("정제 전후 비교 (단과대학별 응답자 수)")

    col_name = '소속단과대학' if '소속단과대학' in clean_df.columns else '단과대학'

    if col_name in clean_df.columns:
        clean_counts = clean_df[col_name].value_counts().rename("정제 후")

        if raw_df is not None and col_name in raw_df.columns:
            raw_counts = raw_df[col_name].value_counts().rename("정제 전")
            # 정제 전후 데이터를 병합하여 차트에 전달
            compare_df = pd.concat([raw_counts, clean_counts], axis=1).fillna(0)
            st.bar_chart(compare_df, horizontal=True)
        else:
            st.info("원본 데이터(raw_df)가 없어 정제 후 데이터만 표시합니다.")
            st.bar_chart(clean_counts, horizontal=True)


def show_analysis_tabs(df):
    # 4개의 탭 생성
    tab1, tab2, tab3, tab4 = st.tabs(["응답자 구성", "문항별 평균", "집단 비교", "사용 시간과 점수"])

    with tab1:
        st.subheader("응답자 구성")
        col1, col2 = st.columns(2)
        with col1:
            st.write("학년별 분포")
            if '학년' in df.columns:
                st.bar_chart(df['학년'].value_counts(), horizontal=True)
        with col2:
            st.write("성별 분포")
            if '성별' in df.columns:
                st.bar_chart(df['성별'].value_counts(), horizontal=True)

    with tab2:
        st.subheader("문항별 평균")
        # 역문항(Q6R) 제외하고 기본 설문(Q1~Q6)만 추출하여 평균 계산
        q_cols = [c for c in df.columns if c.startswith('Q') and c != 'Q6R']
        if q_cols:
            q_means = df[q_cols].apply(pd.to_numeric, errors='coerce').mean()
            st.bar_chart(q_means, horizontal=True)

    with tab3:
        st.subheader("집단 비교")
        col_college = '소속단과대학' if '소속단과대학' in df.columns else '단과대학'
        target_cols = [c for c in ['AI활용점수', 'AI윤리의식'] if c in df.columns]

        if target_cols and col_college in df.columns and '학년' in df.columns:
            # 단과대학별 인원 수 및 평균 점수 병합 (소수점 둘째 자리)
            st.write("단과대학별 분석")
            college_mean = df.groupby(col_college)[target_cols].mean().round(2)
            college_count = df.groupby(col_college).size().rename('인원 수')
            st.dataframe(pd.concat([college_count, college_mean], axis=1))

            # 학년별 인원 수 및 평균 점수 병합 (소수점 둘째 자리)
            st.write("학년별 분석")
            grade_mean = df.groupby('학년')[target_cols].mean().round(2)
            grade_count = df.groupby('학년').size().rename('인원 수')
            st.dataframe(pd.concat([grade_count, grade_mean], axis=1))

    with tab4:
        st.subheader("사용 시간과 점수 분포")
        if 'AI사용시간' in df.columns:
            col1, col2 = st.columns(2)
            # 산점도로 변수 간 분포 확인
            with col1:
                if 'AI활용점수' in df.columns:
                    st.write("AI사용시간과 AI활용점수")
                    st.scatter_chart(df, x='AI사용시간', y='AI활용점수')
            with col2:
                if 'AI윤리의식' in df.columns:
                    st.write("AI사용시간과 AI윤리의식")
                    st.scatter_chart(df, x='AI사용시간', y='AI윤리의식')


def main():
    st.title("그래프 분석")

    clean_df, raw_df = get_data()

    if clean_df is not None:
        df = calculate_derived_scores(clean_df)

        show_summary_metrics(df)
        st.divider()

        show_before_after_comparison(df, raw_df)
        st.divider()

        show_analysis_tabs(df)


if __name__ == "__main__":
    main()