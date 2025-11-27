import os
import zipfile
import tempfile
import streamlit as st
from modified_buried_volume import BuriedVolume
from io import BytesIO
from PIL import Image
import base64
import time
import numpy as np

# 设置环境变量
os.environ['QT_QPA_FONTDIR'] = 'C:/Windows/Fonts'

# 清理临时目录
# 初始化逻辑：仅在页面首次加载时运行一次
if 'page_initialized' not in st.session_state:
    # 清理旧的临时目录（如果存在）
    if 'temp_dir' in st.session_state:
        st.session_state.temp_dir.cleanup()
        del st.session_state.temp_dir
    # 清理旧的结果数据（如果存在）
    if 'result_data' in st.session_state:
        del st.session_state.result_data
    # 标记页面已初始化，避免重复清理
    st.session_state.page_initialized = True

# 设定标题和图标
st.title("WebBV")
st.markdown(
    """
    <h1 style="margin-bottom: 0.8rem; font-size: 1.5rem;">
        A Buried Volume Calculator based on 
        <a href="https://digital-chemistry-laboratory.github.io/morfeus/" target="_blank" 
           style="color: #2e86c1; text-decoration: none;">
            Morfeus
        </a>
        <br>
        <small style="font-size: 16px;">
            <strong>Developed by </strong>
            <a href="https://orcid.org/0009-0001-5735-9343" target="_blank" 
               style="color: #2e86c1; text-decoration: none;">
                <strong>Tang Kun</strong>
            </a>
            <strong>2025.02.25</strong>
        </small>
    </h1>
    """,
    unsafe_allow_html=True
)
img = Image.open('./icon.png')
# img_resized = img.resize((200, 200))
# 将图片转换为 base64 字符串
buffered = BytesIO()
img.save(buffered, format="PNG")  # 保存原图片到缓冲区
# img_resized.save(buffered, format="PNG")
img_base64 = base64.b64encode(buffered.getvalue()).decode()
# 构造居中 HTML 代码
html_code = f"""
<div style="text-align: center;">
    <img src="data:image/jpeg;base64,{img_base64}" style="max-width: 80%;">
</div>
"""
# 渲染居中图片
st.markdown(html_code, unsafe_allow_html=True)

# 初始化临时文件和结果存储变量
if 'temp_dir' not in st.session_state:
    st.session_state.temp_dir = tempfile.TemporaryDirectory()

user_file = st.file_uploader("Please upload an xyz file", type=['xyz'])
if user_file is not None:
    content = user_file.getvalue().decode("utf-8")
    all_lines = content.splitlines()
    if len(all_lines) < 2:
        st.error("Please ensure that you upload a valid XYZ file.")
    else:
        try:
            atom_count = int(all_lines[0].strip())
            st.success(f"Successfully uploaded XYZ file, the molecule contains {atom_count} atoms.")
        except ValueError:
            st.error("The uploaded file format is incorrect.")

with st.form(key="form1"):  # 表单中只负责计算数据并存储到内存中，不涉及文件下载等功能
    center_index = st.number_input(
        'Please enter the central atom index',
        value=0, min_value=0, step=1,
        help='Usually the metal center or the coordinating atom of the organic ligand'
    )

    z_axis_atoms_index = st.number_input(
        'Please enter the atom index for the z-axis direction',
        value=0, min_value=0, step=1,
        help='Determines the orientation of the top view'
    )

    xz_plane_atoms_index = st.number_input(
        'Please enter the atom index that defines the xz plane',
        value=0, min_value=0, step=1,
        help='i.e., the atom index for the x-axis direction'
    )

    excluded_atoms_input = st.text_input(
        'Please enter the atom indices to be excluded',
        help='Separate with commas, or leave blank'
    )

    excluded_atoms = []
    if excluded_atoms_input:
        excluded_atoms = [
            int(i) for i in
            excluded_atoms_input.replace('，', ',').split(',')
            if i.strip().isdigit()
        ]

    sphere_radius = st.number_input(
        'Please enter the sphere radius',
        value=3.5, min_value=0.0, step=0.1,
        help='The sphere radius for drawing the buried volume map, default is 3.5 Å'
    )

    include_hs = st.checkbox('Include hydrogen atoms in calculation')

    reverse_z = st.checkbox('Draw view from opposite direction of z-axis atom')

    run = st.form_submit_button("Run Calculation")

    if run and user_file:
        st.session_state.calculating = True
        progress_bar = st.progress(0)
        starting_text = st.empty()
        starting_text.write("Calculating...")

        # 处理XYZ文件内容
        ligand_name = os.path.splitext(user_file.name)[0]
        # elements, coordinates = read_xyz(xyz_file_path)  # 使用这个函数读取需要给出xyz文件路径
        # 删除文件内容中的初始两行（标题/空行 和 原子数量）
        del (all_lines[0])  # 删除标题/空行
        del (all_lines[0])  # 删除原子数量行
        # 如果存在最终空行，删除它
        all_lines = [line for line in all_lines if line.strip()]
        # 初始化原子列表和坐标列表
        atoms = []
        coor_x = []
        coor_y = []
        coor_z = []
        # 分割文件内容以获取原子信息和坐标
        for line in all_lines:
            split = line.split()
            try:  # 支持数字或符号形式的两种原子名称输入方式
                atoms.append(int(split[0]))
            except:
                atoms.append(split[0])
            coor_x.append(float(split[1]))
            coor_y.append(float(split[2]))
            coor_z.append(float(split[3]))
        # 将原子列表和坐标列表组合成 Morfeus 需要的格式
        print(all_lines)
        elements = np.array(atoms)
        coordinates = list(zip(coor_x, coor_y, coor_z))

        z_axis_atoms = [z_axis_atoms_index]
        xz_plane_atoms = [xz_plane_atoms_index]

        # 执行计算
        bv = BuriedVolume(elements, coordinates, center_index,
                          excluded_atoms=excluded_atoms,
                          z_axis_atoms=z_axis_atoms,
                          xz_plane_atoms=xz_plane_atoms,
                          radius=sphere_radius,
                          include_hs=include_hs,
                          reverse_z=reverse_z,
                          )

        progress_bar.progress(80)
        # 在关键进度更新后添加短暂延迟
        time.sleep(0.3)  # 0.3秒延迟让用户感知进度变化

        # 计算埋藏体积
        fraction_buried_volume = bv.fraction_buried_volume * 100

        # 保存结果到内存
        result_content = f"""Ligand name: {ligand_name}
Fraction buried volume: {bv.fraction_buried_volume}
metal_index: {center_index}
z_axis_atoms_index: {z_axis_atoms_index}
xz_plane_atoms_index: {xz_plane_atoms_index}
Reverse_z: {reverse_z}"""

        # 生成图片到内存
        img_buffer = BytesIO()
        bv.plot_steric_map(filename=img_buffer, cmap="jet")
        img_buffer.seek(0)

        # 存储结果到会话状态
        st.session_state.result_data = {
            "fraction": fraction_buried_volume,
            "image": img_buffer.getvalue(),
            "ligand_name": ligand_name,
            "report": result_content.encode()  # 文本报告二进制数据
        }
        st.session_state.calculating = False

        progress_bar.progress(100)
        starting_text.write("")  # 删除启动提示
        # progress_bar.empty()  # 删除进度条

if 'page_initialized' in st.session_state and 'result_data' in st.session_state:
    st.success("✅ Calculation completed!")  # Display completion mark
    # 持久化显示结果以及下载按钮
    data = st.session_state.result_data
    ligand_name = data["ligand_name"]
    st.image(BytesIO(data["image"]), caption="Buried Volume Steric Map")
    st.write(f"Buried Volume Percentage: {data['fraction']:.2f}%")

    # 下载按钮
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Download Report",
            data=data["report"],
            file_name=f"{ligand_name}_report.txt",
            mime="text/plain"
        )
    with col2:
        st.download_button(
            label="Download Steric Map",
            data=data["image"],
            file_name=f"{ligand_name}_steric_map.png",
            mime="image/png"
        )

    # ZIP打包下载按钮单独放置
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        zip_file.writestr(
            f"{ligand_name}_report.txt",
            st.session_state.result_data["report"]
        )
        zip_file.writestr(
            f"{ligand_name}_steric_map.png",
            st.session_state.result_data["image"]
        )
    zip_buffer.seek(0)

    st.download_button(
        label="Download Complete Results (ZIP)",
        data=zip_buffer,
        file_name=f"{ligand_name}_results.zip",
        mime="application/zip"
    )