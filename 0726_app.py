import streamlit as st
import pandas as pd

def calculate_reference_rewards(cpi, reward_threshold_percent, num_tasks, task_data):
    """计算参考奖励金额"""
    reward_threshold = reward_threshold_percent / 100  # 转换为小数
    base = (cpi * reward_threshold) / num_tasks
    rewards = []
    for _, row in task_data.iterrows():
        if row['达成率'] > 0:
            reward = base / (row['达成率'] / 100)  # 达成率转换为小数
        else:
            reward = 0
        rewards.append(round(reward, 2))
    return rewards

def calculate_adjusted_ratio(cpi, task_data, column_name):
    """计算奖励占比"""
    weighted = (task_data[column_name] * (task_data['达成率'] / 100)).sum()
    return round(weighted / cpi * 100, 2)  # 返回百分比

def main():
    st.title("任务奖励计算器")
    
    # 初始化session state
    if 'phase' not in st.session_state:
        st.session_state.phase = 1  # 1:输入阶段, 2:调整阶段, 3:结果阶段
        st.session_state.task_data = None
        st.session_state.reference_data = None
        st.session_state.adjusted_data = None
        st.session_state.num_tasks = 6  # 默认任务数量
    
    # 顶部筛选框（始终显示）
    st.header("基础参数设置")
    col1, col2, col3 = st.columns(3)
    with col1:
        cpi = st.number_input("CPI", min_value=0.0, value=2.0, step=0.1, key="cpi_input")
    with col2:
        reward_threshold_percent = st.number_input(
            "奖励阈值(%)", 
            min_value=0.0, 
            max_value=100.0, 
            value=20.0, 
            step=1.0,
            format="%.1f",
            key="reward_threshold_input"
        )
    with col3:
        num_tasks = st.number_input("任务数量", min_value=1, value=st.session_state.num_tasks, step=1, key="num_tasks_input")
        st.session_state.num_tasks = num_tasks
    
    # 第一阶段：任务达成率输入
    st.header("第一阶段：任务达成率输入")
    
    # 初始化或更新任务数据
    if st.session_state.task_data is None or len(st.session_state.task_data) != num_tasks:
        st.session_state.task_data = pd.DataFrame({
            '任务名称': [f'任务{i+1}' for i in range(num_tasks)],
            '达成率': [100.0] * num_tasks
        })
    
    # 显示可编辑表格
    edited_data = st.data_editor(
        st.session_state.task_data,
        column_config={
            "达成率": st.column_config.NumberColumn(
                format="%.2f %%",
                min_value=0.0,
                max_value=1000.0
            )
        },
        num_rows="fixed",
        key="task_editor"
    )
    
    if st.button("生成参考奖励", key="generate_reference"):
        if edited_data.isnull().values.any():
            st.error("请填写所有任务名称和达成率")
        else:
            st.session_state.task_data = edited_data
            # 计算参考奖励
            ref_rewards = calculate_reference_rewards(cpi, reward_threshold_percent, num_tasks, edited_data)
            
            # 准备参考数据
            st.session_state.reference_data = edited_data.copy()
            st.session_state.reference_data['参考奖励金额($)'] = ref_rewards
            st.session_state.reference_data['调整后奖励金额($)'] = ref_rewards
            
            st.session_state.phase = 2
            st.rerun()
    
    # 第二阶段：奖励金额调整（简化版）
    if st.session_state.phase >= 2 and st.session_state.reference_data is not None:
        st.header("第二阶段：奖励金额调整")
        st.write("请调整奖励金额（初始值为参考奖励金额）")
        
        # 单个可编辑表格（替换原来的两个表格）
        adjusted_data = st.data_editor(
            st.session_state.reference_data,
            column_config={
                "达成率": st.column_config.NumberColumn(
                    format="%.2f %%",
                    disabled=True
                ),
                "参考奖励金额($)": st.column_config.NumberColumn(
                    format="%.2f $",
                    disabled=True
                ),
                "调整后奖励金额($)": st.column_config.NumberColumn(
                    format="%.2f $",
                    min_value=0.0
                )
            },
            num_rows="fixed",
            key="reward_editor"
        )
        
        if st.button("确认最终奖励", key="confirm_final"):
            st.session_state.adjusted_data = adjusted_data
            st.session_state.phase = 3
            st.rerun()
    
    # 第三阶段：结果总结（始终显示，但内容根据phase变化）
    if st.session_state.phase == 3 and st.session_state.adjusted_data is not None:
        st.header("第三阶段：结果总结")
        st.success("奖励分配已完成！")
        
        # 显示最终结果表格
        st.dataframe(st.session_state.adjusted_data.style.format({
            '达成率': '{:.2f} %',
            '参考奖励金额($)': '{:.2f} $',
            '调整后奖励金额($)': '{:.2f} $'
        }), hide_index=True)
        
        # 计算参考奖励指标
        ref_total = st.session_state.adjusted_data['参考奖励金额($)'].sum()
        ref_weighted = (st.session_state.adjusted_data['达成率'] / 100 * 
                       st.session_state.adjusted_data['参考奖励金额($)']).sum()
        ref_ratio = calculate_adjusted_ratio(cpi, st.session_state.adjusted_data, '参考奖励金额($)')
        
        # 计算调整后奖励指标
        adj_total = st.session_state.adjusted_data['调整后奖励金额($)'].sum()
        adj_weighted = (st.session_state.adjusted_data['达成率'] / 100 * 
                       st.session_state.adjusted_data['调整后奖励金额($)']).sum()
        adj_ratio = calculate_adjusted_ratio(cpi, st.session_state.adjusted_data, '调整后奖励金额($)')
        
        # 显示统计信息
        st.subheader("统计摘要")
        
        # 参考奖励指标
        st.markdown("**参考奖励指标**")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("累计奖励金额", f"{ref_total:.2f} $")
        with col2:
            st.metric("加权奖励金额", f"{ref_weighted:.2f} $")
        with col3:
            st.metric("奖励占比", f"{ref_ratio:.2f} %")
        
        # 调整后奖励指标
        st.markdown("**调整后奖励指标**")
        col4, col5, col6 = st.columns(3)
        with col4:
            st.metric("累计奖励金额", f"{adj_total:.2f} $")
        with col5:
            st.metric("加权奖励金额", f"{adj_weighted:.2f} $")
        with col6:
            st.metric("奖励占比", f"{adj_ratio:.2f} %")
    
    # 重置按钮（始终显示）
    if st.button("重新开始", key="restart"):
        st.session_state.phase = 1
        st.session_state.task_data = None
        st.session_state.reference_data = None
        st.session_state.adjusted_data = None
        st.rerun()

if __name__ == "__main__":
    main()
