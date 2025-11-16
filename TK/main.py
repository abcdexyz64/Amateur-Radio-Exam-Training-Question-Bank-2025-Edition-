#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
业余无线电考试模拟训练系统
支持模拟考试、关键字搜题、顺序刷题等功能
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import re
import random
from typing import List, Dict, Optional, Set
from datetime import datetime
import os
from PIL import Image, ImageTk


class Question:
    """题目类"""
    def __init__(self):
        self.j_id = ""  # 题号
        self.p_id = ""  # 章节
        self.i_id = ""  # 内部编号
        self.question = ""  # 问题
        self.answer = ""  # 正确答案（如"A"或"AC"）
        self.options = {}  # 选项字典 {A: "选项内容", B: "选项内容", ...}
        self.image_path = None  # 图片路径（如果有）
    
    def __str__(self):
        return f"[{self.j_id}] {self.question[:50]}..."


class QuestionBank:
    """题库类"""
    def __init__(self):
        self.questions: List[Question] = []
        self.photo_dir = ""  # 图片文件夹路径
    
    def load_from_file(self, filepath: str, photo_dir: str = None) -> bool:
        """从txt文件加载题库"""
        try:
            # 如果指定了photo_dir，使用指定的；否则尝试从filepath推断
            if photo_dir:
                self.photo_dir = photo_dir
            else:
                # 尝试从文件路径推断photo目录
                file_dir = os.path.dirname(filepath)
                potential_photo_dir = os.path.join(file_dir, "photo")
                if os.path.exists(potential_photo_dir):
                    self.photo_dir = potential_photo_dir
                else:
                    # 如果当前目录有TK/photo，使用它
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    tk_photo_dir = os.path.join(base_dir, "TK", "photo")
                    if os.path.exists(tk_photo_dir):
                        self.photo_dir = tk_photo_dir
                    else:
                        self.photo_dir = ""
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 按题目分割（每个题目以[J]开头）
            pattern = r'\[J\](.*?)(?=\[J\]|$)'
            matches = re.findall(pattern, content, re.DOTALL)
            
            self.questions = []
            for match in matches:
                question = self._parse_question(match)
                if question:
                    self.questions.append(question)
            
            # 打印调试信息
            if self.photo_dir:
                print(f"图片目录: {os.path.abspath(self.photo_dir)}")
                print(f"图片目录存在: {os.path.exists(self.photo_dir)}")
                # 统计有图片的题目数量
                image_count = sum(1 for q in self.questions if q.image_path)
                print(f"找到 {image_count} 道带图片的题目")
            
            return len(self.questions) > 0
        except Exception as e:
            messagebox.showerror("错误", f"加载题库失败：{str(e)}")
            return False
    
    def _parse_question(self, text: str) -> Optional[Question]:
        """解析单个题目"""
        try:
            q = Question()
            
            # 提取各个字段
            j_match = re.search(r'\[J\]([^\n]+)', text)
            if j_match:
                q.j_id = j_match.group(1).strip()
            
            p_match = re.search(r'\[P\]([^\n]+)', text)
            if p_match:
                q.p_id = p_match.group(1).strip()
            
            i_match = re.search(r'\[I\]([^\n]+)', text)
            if i_match:
                q.i_id = i_match.group(1).strip()
            
            q_match = re.search(r'\[Q\]([^\n]+)', text)
            if q_match:
                q.question = q_match.group(1).strip()
            
            t_match = re.search(r'\[T\]([^\n]+)', text)
            if t_match:
                q.answer = t_match.group(1).strip()
            
            # 提取选项
            for option in ['A', 'B', 'C', 'D']:
                pattern = rf'\[{option}\]([^\n]+)'
                opt_match = re.search(pattern, text)
                if opt_match:
                    q.options[option] = opt_match.group(1).strip()
            
            # 提取图片文件名 [F]字段
            f_match = re.search(r'\[F\]([^\n]+)', text)
            if f_match:
                image_filename = f_match.group(1).strip()
                # 构建图片路径
                if self.photo_dir:
                    abs_photo_dir = os.path.abspath(self.photo_dir)
                    
                    # 首先尝试使用原始文件名
                    image_path = os.path.join(abs_photo_dir, image_filename)
                    
                    # 如果文件不存在，尝试其他扩展名（.jpg, .png, .jpeg）
                    if not os.path.exists(image_path):
                        # 获取文件名（不含扩展名）
                        base_name = os.path.splitext(image_filename)[0]
                        # 尝试不同的扩展名
                        for ext in ['.jpg', '.png', '.jpeg', '.JPG', '.PNG', '.JPEG']:
                            alt_path = os.path.join(abs_photo_dir, base_name + ext)
                            if os.path.exists(alt_path):
                                image_path = alt_path
                                break
                    
                    # 检查最终路径是否存在
                    if os.path.exists(image_path):
                        q.image_path = os.path.abspath(image_path)
                    else:
                        # 如果图片不存在，打印调试信息
                        print(f"图片文件不存在: {image_filename} (尝试路径: {image_path})")
                        q.image_path = None
                else:
                    print(f"警告: photo_dir未设置，无法加载图片 {image_filename}")
                    q.image_path = None
            
            return q if q.question else None
        except Exception as e:
            print(f"解析题目失败：{str(e)}")
            return None
    
    def _fuzzy_match(self, pattern: str, text: str) -> bool:
        """模糊匹配：支持大小写不敏感和近似字符匹配（处理l/I/1, O/0等易混淆字符）"""
        if not pattern or not text:
            return False
        
        # 首先尝试直接匹配（大小写不敏感）
        pattern_lower = pattern.lower()
        text_lower = text.lower()
        if pattern_lower in text_lower:
            return True
        
        # 近似匹配：处理容易混淆的字符
        def normalize_char(c):
            """将容易混淆的字符标准化
            l/I/1 -> 'i' (小写i)
            O/0 -> '0' (数字0)
            o -> 'o' (小写o)
            """
            c_lower = c.lower()
            if c_lower in ['l', 'i', '1']:
                # l, I, 1 都映射为 'i'
                return 'i'
            elif c_lower in ['o', '0']:
                # o, O, 0 都映射为 '0' (注意：这里O和0都映射为0，因为容易混淆)
                return '0'
            else:
                return c_lower
        
        # 标准化模式和目标文本
        pattern_normalized = ''.join(normalize_char(c) for c in pattern)
        text_normalized = ''.join(normalize_char(c) for c in text)
        
        # 检查标准化后的文本是否包含模式
        if pattern_normalized in text_normalized:
            return True
        
        return False
    
    def search_by_keyword(self, keyword: str) -> List[Question]:
        """关键字搜题（支持大小写不敏感和近似搜索）"""
        if not keyword:
            return self.questions
        keyword = keyword.strip()
        results = []
        for q in self.questions:
            # 使用模糊匹配
            if (self._fuzzy_match(keyword, q.question) or 
                self._fuzzy_match(keyword, q.j_id) or
                self._fuzzy_match(keyword, q.p_id) or
                any(self._fuzzy_match(keyword, opt) for opt in q.options.values())):
                results.append(q)
        return results
    
    def search_by_chapter(self, chapter: str) -> List[Question]:
        """按章节搜题（支持部分匹配和近似搜索，如搜索"1.2"可找到所有1.2.x的题目）"""
        if not chapter:
            return self.questions
        chapter = chapter.strip()
        results = []
        for q in self.questions:
            # 使用模糊匹配，支持部分匹配和近似字符
            if self._fuzzy_match(chapter, q.p_id):
                results.append(q)
        return results
    
    def search_by_id(self, question_id: str) -> List[Question]:
        """按编号搜题（只搜索[I]字段，支持部分匹配和近似搜索，如搜索"MC"可找到所有MC编号的题）"""
        if not question_id:
            return self.questions
        question_id = question_id.strip()
        results = []
        for q in self.questions:
            # 只搜索内部编号i_id字段，使用模糊匹配
            if self._fuzzy_match(question_id, q.i_id):
                results.append(q)
        return results


class ExamApp:
    """主应用程序类"""
    def __init__(self, root):
        self.root = root
        self.root.title("业余无线电考试模拟训练系统")
        self.root.geometry("900x700")
        
        self.bank = QuestionBank()
        self.current_questions: List[Question] = []
        self.current_index = 0
        self.exam_mode = False
        self.exam_answers = {}  # 考试模式下的用户答案
        self.exam_start_time = None
        self.search_mode = False  # 是否在搜题模式
        self.before_search_state = None  # 搜题前的状态 (questions, index)
        
        self.setup_ui()
    
    def setup_ui(self):
        """设置用户界面"""
        # 菜单栏
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="文件", menu=file_menu)
        file_menu.add_command(label="导入题库", command=self.load_question_bank)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部工具栏
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(toolbar, text="导入题库", command=self.load_question_bank).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="顺序刷题", command=self.start_sequential_mode).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="模拟考试", command=self.start_exam_mode).pack(side=tk.LEFT, padx=5)
        ttk.Button(toolbar, text="关键字搜题", command=self.show_search_dialog).pack(side=tk.LEFT, padx=5)
        
        # 返回按钮（搜题模式下显示）
        self.back_button = ttk.Button(toolbar, text="返回", command=self.back_from_search, state=tk.DISABLED)
        self.back_button.pack(side=tk.LEFT, padx=5)
        
        # 状态栏
        self.status_label = ttk.Label(toolbar, text="请先导入题库", foreground="gray")
        self.status_label.pack(side=tk.RIGHT, padx=5)
        
        # 题目显示区域
        question_frame = ttk.LabelFrame(main_frame, text="题目", padding="10")
        question_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 题号显示
        self.question_id_label = ttk.Label(question_frame, text="", font=("Arial", 10, "bold"))
        self.question_id_label.pack(anchor=tk.W, pady=(0, 5))
        
        # 问题内容
        self.question_text = scrolledtext.ScrolledText(
            question_frame, height=3, wrap=tk.WORD, font=("Arial", 11)
        )
        self.question_text.pack(fill=tk.X, pady=(0, 10))
        self.question_text.config(state=tk.DISABLED)
        
        # 图片显示区域
        self.image_label = ttk.Label(question_frame, text="")
        self.image_label.pack(pady=5)
        self.current_image = None  # 保存当前图片引用，防止被垃圾回收
        
        # 选项区域
        self.option_vars = {}
        self.option_buttons = {}
        self.options_frame = ttk.Frame(question_frame)
        self.options_frame.pack(fill=tk.BOTH, expand=True)
        
        # 答案显示区域
        self.answer_label = ttk.Label(
            question_frame, 
            text="", 
            font=("Arial", 11, "bold"),
            foreground="green"
        )
        self.answer_label.pack(pady=10)
        
        # 底部控制按钮
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X)
        
        ttk.Button(control_frame, text="上一题", command=self.prev_question).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="下一题", command=self.next_question).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="显示答案", command=self.show_answer).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="清除选择", command=self.clear_selection).pack(side=tk.LEFT, padx=5)
        
        if self.exam_mode:
            ttk.Button(control_frame, text="提交考试", command=self.submit_exam).pack(side=tk.RIGHT, padx=5)
    
    def load_question_bank(self):
        """加载题库 - 选择A/B/C/All或自定义题库"""
        # 获取当前脚本所在目录
        base_dir = os.path.dirname(os.path.abspath(__file__))
        tk_dir = os.path.join(base_dir, "TK")
        photo_dir = os.path.join(tk_dir, "photo")
        
        # 创建选择对话框
        dialog = tk.Toplevel(self.root)
        dialog.title("选择题库")
        dialog.geometry("350x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 主框架
        main_dialog_frame = ttk.Frame(dialog, padding="10")
        main_dialog_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_dialog_frame, text="请选择要加载的题库：", font=("Arial", 10)).pack(pady=10)
        
        # 选项框架
        options_frame = ttk.Frame(main_dialog_frame)
        options_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        bank_files = {
            "A级题库": "A.txt",
            "B级题库": "B.txt",
            "C级题库": "C.txt",
            "全部题库": "All.txt",
            "自定义题库": "CUSTOM"
        }
        
        selected_bank = tk.StringVar()
        
        # 检查TK文件夹是否存在
        tk_exists = os.path.exists(tk_dir)
        
        for bank_name, bank_file in bank_files.items():
            if bank_name == "自定义题库":
                # 自定义题库选项始终可用
                ttk.Radiobutton(
                    options_frame,
                    text=bank_name,
                    variable=selected_bank,
                    value=bank_file
                ).pack(anchor=tk.W, padx=50, pady=3)
            else:
                # 内置题库选项
                if tk_exists:
                    filepath = os.path.join(tk_dir, bank_file)
                    if os.path.exists(filepath):
                        ttk.Radiobutton(
                            options_frame,
                            text=bank_name,
                            variable=selected_bank,
                            value=bank_file
                        ).pack(anchor=tk.W, padx=50, pady=3)
                    else:
                        # 文件不存在，显示但禁用
                        rb = ttk.Radiobutton(
                            options_frame,
                            text=f"{bank_name} (不存在)",
                            variable=selected_bank,
                            value=bank_file,
                            state=tk.DISABLED
                        )
                        rb.pack(anchor=tk.W, padx=50, pady=3)
                else:
                    # TK文件夹不存在，显示但禁用
                    rb = ttk.Radiobutton(
                        options_frame,
                        text=f"{bank_name} (TK文件夹不存在)",
                        variable=selected_bank,
                        value=bank_file,
                        state=tk.DISABLED
                    )
                    rb.pack(anchor=tk.W, padx=50, pady=3)
        
        # 按钮框架
        button_frame = ttk.Frame(main_dialog_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        def confirm_load():
            bank_file = selected_bank.get()
            if not bank_file:
                messagebox.showwarning("警告", "请选择一个题库！")
                return
            
            if bank_file == "CUSTOM":
                # 自定义题库：打开文件选择对话框
                dialog.destroy()
                filepath = filedialog.askopenfilename(
                    title="选择自定义题库文件",
                    filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
                )
                if filepath:
                    # 尝试推断photo目录
                    file_dir = os.path.dirname(filepath)
                    potential_photo_dir = os.path.join(file_dir, "photo")
                    if not os.path.exists(potential_photo_dir) and tk_exists:
                        potential_photo_dir = photo_dir
                    
                    if self.bank.load_from_file(filepath, potential_photo_dir):
                        self.current_questions = self.bank.questions
                        self.current_index = 0
                        self.exam_mode = False
                        self.search_mode = False
                        self.back_button.config(state=tk.DISABLED)
                        self.status_label.config(
                            text=f"已加载 {len(self.bank.questions)} 道题目（自定义）",
                            foreground="green"
                        )
                        self.display_question()
                        messagebox.showinfo("成功", f"成功加载 {len(self.bank.questions)} 道题目！")
                    else:
                        self.status_label.config(text="加载题库失败", foreground="red")
            else:
                # 内置题库
                if not tk_exists:
                    messagebox.showerror("错误", "未找到TK文件夹！请确保TK文件夹与main.py在同一目录下。")
                    dialog.destroy()
                    return
                
                filepath = os.path.join(tk_dir, bank_file)
                if not os.path.exists(filepath):
                    messagebox.showerror("错误", f"题库文件不存在：{filepath}")
                    dialog.destroy()
                    return
                
                # 加载题库，指定photo目录
                if self.bank.load_from_file(filepath, photo_dir):
                    self.current_questions = self.bank.questions
                    self.current_index = 0
                    self.exam_mode = False
                    self.search_mode = False
                    self.back_button.config(state=tk.DISABLED)
                    self.status_label.config(
                        text=f"已加载 {len(self.bank.questions)} 道题目",
                        foreground="green"
                    )
                    self.display_question()
                    messagebox.showinfo("成功", f"成功加载 {len(self.bank.questions)} 道题目！")
                    dialog.destroy()
                else:
                    self.status_label.config(text="加载题库失败", foreground="red")
                    dialog.destroy()
        
        # 确认和取消按钮
        ttk.Button(button_frame, text="确定", command=confirm_load, width=12).pack(side=tk.LEFT, padx=5, expand=True)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=12).pack(side=tk.LEFT, padx=5, expand=True)
    
    def start_sequential_mode(self):
        """开始顺序刷题模式"""
        if not self.bank.questions:
            messagebox.showwarning("警告", "请先导入题库！")
            return
        
        self.exam_mode = False
        self.search_mode = False
        self.current_questions = self.bank.questions
        self.current_index = 0
        self.back_button.config(state=tk.DISABLED)  # 隐藏返回按钮
        self.status_label.config(
            text=f"顺序刷题模式 - 第 {self.current_index + 1}/{len(self.current_questions)} 题",
            foreground="blue"
        )
        self.display_question()
    
    def start_exam_mode(self):
        """开始模拟考试模式"""
        if not self.bank.questions:
            messagebox.showwarning("警告", "请先导入题库！")
            return
        
        # 询问考试题目数量
        dialog = tk.Toplevel(self.root)
        dialog.title("模拟考试设置")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="请输入考试题目数量：").pack(pady=10)
        
        count_var = tk.StringVar(value=str(min(100, len(self.bank.questions))))
        count_entry = ttk.Entry(dialog, textvariable=count_var, width=20)
        count_entry.pack(pady=5)
        
        def confirm_exam():
            try:
                count = int(count_var.get())
                if count <= 0 or count > len(self.bank.questions):
                    messagebox.showerror("错误", f"题目数量应在 1-{len(self.bank.questions)} 之间！")
                    return
                
                # 随机选择题目
                self.exam_mode = True
                self.search_mode = False
                self.current_questions = random.sample(self.bank.questions, count)
                self.current_index = 0
                self.exam_answers = {}
                self.exam_start_time = datetime.now()
                self.back_button.config(state=tk.DISABLED)  # 隐藏返回按钮
                
                self.status_label.config(
                    text=f"模拟考试模式 - 第 {self.current_index + 1}/{len(self.current_questions)} 题",
                    foreground="red"
                )
                
                # 更新界面（隐藏答案显示）
                self.answer_label.config(text="")
                self.display_question()
                
                dialog.destroy()
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字！")
        
        ttk.Button(dialog, text="开始考试", command=confirm_exam).pack(pady=10)
        count_entry.focus()
        count_entry.bind('<Return>', lambda e: confirm_exam())
    
    def show_search_dialog(self):
        """显示搜题对话框（支持关键字、章节、编号）"""
        if not self.bank.questions:
            messagebox.showwarning("警告", "请先导入题库！")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("搜题")
        dialog.geometry("450x350")
        dialog.transient(self.root)
        
        # 主框架
        main_frame = ttk.Frame(dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="请选择搜题方式：", font=("Arial", 10, "bold")).pack(pady=10)
        
        # 搜题方式选择
        search_type = tk.StringVar(value="keyword")
        
        search_frame = ttk.LabelFrame(main_frame, text="搜题方式", padding="10")
        search_frame.pack(fill=tk.X, pady=10)
        
        ttk.Radiobutton(
            search_frame,
            text="关键字搜题（在题目、选项、题号中搜索，支持大小写不敏感和近似匹配）",
            variable=search_type,
            value="keyword"
        ).pack(anchor=tk.W, pady=3)
        
        ttk.Radiobutton(
            search_frame,
            text="按章节搜题（支持部分匹配和近似搜索，如：1.2 可找到所有1.2.x的题目）",
            variable=search_type,
            value="chapter"
        ).pack(anchor=tk.W, pady=3)
        
        ttk.Radiobutton(
            search_frame,
            text="按编号搜题（搜索[I]字段，支持部分匹配和近似搜索，如：MC 可找到所有MC编号的题）",
            variable=search_type,
            value="id"
        ).pack(anchor=tk.W, pady=3)
        
        # 输入框
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(input_frame, text="请输入搜索内容：").pack(anchor=tk.W, pady=5)
        
        search_var = tk.StringVar()
        search_entry = ttk.Entry(input_frame, textvariable=search_var, width=40)
        search_entry.pack(fill=tk.X, pady=5)
        search_entry.focus()
        
        result_label = ttk.Label(input_frame, text="", foreground="blue")
        result_label.pack(pady=5)
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        def do_search():
            search_text = search_var.get().strip()
            if not search_text:
                messagebox.showwarning("警告", "请输入搜索内容！")
                return
            
            search_mode = search_type.get()
            results = []
            
            if search_mode == "keyword":
                results = self.bank.search_by_keyword(search_text)
            elif search_mode == "chapter":
                results = self.bank.search_by_chapter(search_text)
            elif search_mode == "id":
                results = self.bank.search_by_id(search_text)
            
            if results:
                # 保存搜题前的状态
                if not self.search_mode:
                    self.before_search_state = (self.current_questions.copy(), self.current_index)
                
                self.current_questions = results
                self.current_index = 0
                self.exam_mode = False
                self.search_mode = True
                self.back_button.config(state=tk.NORMAL)  # 显示返回按钮
                
                mode_name = {"keyword": "关键字", "chapter": "章节", "id": "编号"}[search_mode]
                self.status_label.config(
                    text=f"{mode_name}搜索结果 - 找到 {len(results)} 道题目 - 第 {self.current_index + 1}/{len(results)} 题",
                    foreground="purple"
                )
                self.display_question()
                result_label.config(text=f"找到 {len(results)} 道相关题目", foreground="green")
                dialog.destroy()
            else:
                result_label.config(text="未找到相关题目", foreground="red")
        
        ttk.Button(button_frame, text="搜索", command=do_search, width=12).pack(side=tk.LEFT, padx=5, expand=True)
        ttk.Button(button_frame, text="取消", command=dialog.destroy, width=12).pack(side=tk.LEFT, padx=5, expand=True)
        
        search_entry.bind('<Return>', lambda e: do_search())
    
    def back_from_search(self):
        """从搜题模式返回"""
        if self.search_mode and self.before_search_state:
            self.current_questions, self.current_index = self.before_search_state
            self.search_mode = False
            self.back_button.config(state=tk.DISABLED)  # 隐藏返回按钮
            
            # 更新状态栏
            if self.exam_mode:
                self.status_label.config(
                    text=f"模拟考试模式 - 第 {self.current_index + 1}/{len(self.current_questions)} 题",
                    foreground="red"
                )
            else:
                self.status_label.config(
                    text=f"顺序刷题模式 - 第 {self.current_index + 1}/{len(self.current_questions)} 题",
                    foreground="blue"
                )
            
            self.display_question()
        else:
            # 如果没有保存的状态，返回顺序刷题模式
            if self.bank.questions:
                self.start_sequential_mode()
    
    def create_option_widgets(self, question):
        """根据题目类型创建选项控件（单选或多选）"""
        # 清除现有控件
        for widget in self.options_frame.winfo_children():
            widget.destroy()
        self.option_vars = {}
        self.option_buttons = {}
        
        # 判断是单选还是多选
        is_multiple = len(question.answer) > 1
        
        # 创建选项控件
        for option in ['A', 'B', 'C', 'D']:
            if option in question.options:
                text = f"{option}. {question.options[option]}"
                if is_multiple:
                    # 多选题使用Checkbutton
                    var = tk.BooleanVar()
                    self.option_vars[option] = var
                    btn = ttk.Checkbutton(
                        self.options_frame,
                        text=text,
                        variable=var,
                        command=lambda opt=option: self.on_option_selected(opt)
                    )
                else:
                    # 单选题使用Radiobutton，需要共享同一个变量
                    if 'radio_var' not in self.option_vars:
                        self.option_vars['radio_var'] = tk.StringVar()
                    var = self.option_vars['radio_var']
                    self.option_vars[option] = var
                    btn = ttk.Radiobutton(
                        self.options_frame,
                        text=text,
                        variable=var,
                        value=option,
                        command=lambda opt=option: self.on_option_selected(opt)
                    )
                btn.pack(anchor=tk.W, pady=5)
                self.option_buttons[option] = btn
    
    def display_image(self, question):
        """显示题目图片"""
        # 清除之前的图片
        self.image_label.config(image="", text="")
        self.current_image = None
        
        # 如果有图片路径，加载并显示
        if question.image_path:
            # 检查文件是否存在
            if os.path.exists(question.image_path):
                try:
                    # 打开图片
                    img = Image.open(question.image_path)
                    
                    # 调整图片大小（最大宽度600，保持比例）
                    max_width = 600
                    if img.width > max_width:
                        ratio = max_width / img.width
                        new_width = max_width
                        new_height = int(img.height * ratio)
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    # 转换为PhotoImage
                    self.current_image = ImageTk.PhotoImage(img)
                    self.image_label.config(image=self.current_image)
                except Exception as e:
                    error_msg = f"图片加载失败: {str(e)}"
                    print(error_msg)
                    print(f"图片路径: {question.image_path}")
                    self.image_label.config(text=error_msg, foreground="red")
            else:
                error_msg = f"图片文件不存在: {question.image_path}"
                print(error_msg)
                self.image_label.config(text=error_msg, foreground="red")
    
    def display_question(self):
        """显示当前题目"""
        if not self.current_questions or self.current_index >= len(self.current_questions):
            return
        
        question = self.current_questions[self.current_index]
        
        # 显示题号
        self.question_id_label.config(
            text=f"题号: {question.j_id} | 章节: {question.p_id} | 编号: {question.i_id}"
        )
        
        # 显示问题
        self.question_text.config(state=tk.NORMAL)
        self.question_text.delete(1.0, tk.END)
        self.question_text.insert(1.0, question.question)
        self.question_text.config(state=tk.DISABLED)
        
        # 显示图片（如果有）
        self.display_image(question)
        
        # 创建选项控件
        self.create_option_widgets(question)
        
        # 如果是考试模式，显示已选择的答案
        if self.exam_mode and self.current_index in self.exam_answers:
            selected = self.exam_answers[self.current_index]
            is_multiple = len(question.answer) > 1
            if is_multiple:
                # 多选题：设置Checkbutton状态
                for opt in ['A', 'B', 'C', 'D']:
                    if opt in self.option_vars:
                        self.option_vars[opt].set(opt in selected)
            else:
                # 单选题：设置Radiobutton状态
                if selected and len(selected) > 0:
                    if 'radio_var' in self.option_vars:
                        self.option_vars['radio_var'].set(selected[0])
        # 如果是顺序刷题模式（非考试模式且非搜题模式），自动勾选正确答案
        elif not self.exam_mode and not self.search_mode:
            is_multiple = len(question.answer) > 1
            if is_multiple:
                # 多选题：自动勾选所有正确答案
                for opt in question.answer:
                    if opt in self.option_vars:
                        self.option_vars[opt].set(True)
            else:
                # 单选题：自动选择正确答案
                if question.answer and len(question.answer) > 0:
                    if 'radio_var' in self.option_vars:
                        self.option_vars['radio_var'].set(question.answer[0])
        
        # 隐藏答案（考试模式下）
        if self.exam_mode:
            self.answer_label.config(text="")
        else:
            self.answer_label.config(text="")
    
    def on_option_selected(self, option):
        """选项被选择时的回调"""
        if self.exam_mode:
            # 考试模式：支持多选（如果答案是多个字母）
            question = self.current_questions[self.current_index]
            if len(question.answer) > 1:
                # 多选题：直接使用Checkbutton的状态
                if self.current_index not in self.exam_answers:
                    self.exam_answers[self.current_index] = []
                if option in self.option_vars:
                    if self.option_vars[option].get():
                        if option not in self.exam_answers[self.current_index]:
                            self.exam_answers[self.current_index].append(option)
                    else:
                        if option in self.exam_answers[self.current_index]:
                            self.exam_answers[self.current_index].remove(option)
            else:
                # 单选题
                if 'radio_var' in self.option_vars:
                    selected = self.option_vars['radio_var'].get()
                    self.exam_answers[self.current_index] = [selected] if selected else []
    
    def show_answer(self):
        """显示答案"""
        if not self.current_questions or self.current_index >= len(self.current_questions):
            return
        
        question = self.current_questions[self.current_index]
        answer_text = f"正确答案: {question.answer}"
        
        # 检查用户答案（如果有）
        if self.exam_mode and self.current_index in self.exam_answers:
            user_answer = ''.join(sorted(self.exam_answers[self.current_index]))
            correct_answer = ''.join(sorted(question.answer))
            if user_answer == correct_answer:
                answer_text += f" ✓ 您的答案: {user_answer} (正确)"
                self.answer_label.config(foreground="green")
            else:
                answer_text += f" ✗ 您的答案: {user_answer} (错误)"
                self.answer_label.config(foreground="red")
        else:
            self.answer_label.config(foreground="green")
        
        self.answer_label.config(text=answer_text)
    
    def clear_selection(self):
        """清除选择"""
        question = self.current_questions[self.current_index] if self.current_questions else None
        if question:
            is_multiple = len(question.answer) > 1
            if is_multiple:
                # 多选题：清除所有Checkbutton
                for opt in ['A', 'B', 'C', 'D']:
                    if opt in self.option_vars:
                        self.option_vars[opt].set(False)
            else:
                # 单选题：清除Radiobutton
                if 'radio_var' in self.option_vars:
                    self.option_vars['radio_var'].set("")
        if self.exam_mode and self.current_index in self.exam_answers:
            del self.exam_answers[self.current_index]
    
    def prev_question(self):
        """上一题"""
        if self.current_index > 0:
            self.current_index -= 1
            self.update_status()
            self.display_question()
    
    def next_question(self):
        """下一题"""
        if self.current_index < len(self.current_questions) - 1:
            self.current_index += 1
            self.update_status()
            self.display_question()
        elif self.exam_mode:
            # 考试模式下，最后一题后提示提交
            if messagebox.askyesno("提示", "已经是最后一题，是否提交考试？"):
                self.submit_exam()
    
    def update_status(self):
        """更新状态栏"""
        if self.exam_mode:
            self.status_label.config(
                text=f"模拟考试模式 - 第 {self.current_index + 1}/{len(self.current_questions)} 题",
                foreground="red"
            )
        else:
            self.status_label.config(
                text=f"第 {self.current_index + 1}/{len(self.current_questions)} 题",
                foreground="blue"
            )
    
    def submit_exam(self):
        """提交考试"""
        if not self.exam_mode:
            return
        
        # 统计成绩
        total = len(self.current_questions)
        correct = 0
        wrong = 0
        unanswered = 0
        
        for i, question in enumerate(self.current_questions):
            user_answer = ''.join(sorted(self.exam_answers.get(i, [])))
            correct_answer = ''.join(sorted(question.answer))
            if not user_answer:
                unanswered += 1
            elif user_answer == correct_answer:
                correct += 1
            else:
                wrong += 1
        
        # 计算用时
        if self.exam_start_time:
            duration = datetime.now() - self.exam_start_time
            minutes = int(duration.total_seconds() // 60)
            seconds = int(duration.total_seconds() % 60)
            time_str = f"{minutes}分{seconds}秒"
        else:
            time_str = "未知"
        
        # 显示成绩
        score = (correct / total * 100) if total > 0 else 0
        result_text = f"""考试结果

总题数: {total}
正确: {correct}
错误: {wrong}
未答: {unanswered}
得分: {score:.1f}分
用时: {time_str}

是否查看错题？"""
        
        if messagebox.askyesno("考试结果", result_text):
            # 显示错题
            self.show_wrong_questions(correct, wrong, unanswered)
        
        # 退出考试模式
        self.exam_mode = False
        self.status_label.config(text="考试已结束", foreground="gray")
    
    def show_wrong_questions(self, correct, wrong, unanswered):
        """显示错题"""
        wrong_questions = []
        for i, question in enumerate(self.current_questions):
            user_answer = ''.join(sorted(self.exam_answers.get(i, [])))
            correct_answer = ''.join(sorted(question.answer))
            if not user_answer or user_answer != correct_answer:
                wrong_questions.append((i, question, user_answer, correct_answer))
        
        if not wrong_questions:
            messagebox.showinfo("恭喜", "全部答对！")
            return
        
        # 创建错题窗口
        wrong_window = tk.Toplevel(self.root)
        wrong_window.title("错题回顾")
        wrong_window.geometry("800x600")
        
        text_widget = scrolledtext.ScrolledText(wrong_window, wrap=tk.WORD, font=("Arial", 10))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for idx, (i, question, user_ans, correct_ans) in enumerate(wrong_questions, 1):
            text_widget.insert(tk.END, f"\n{'='*60}\n")
            text_widget.insert(tk.END, f"错题 {idx} (原题号: {question.j_id})\n")
            text_widget.insert(tk.END, f"{question.question}\n\n")
            for opt in ['A', 'B', 'C', 'D']:
                if opt in question.options:
                    text_widget.insert(tk.END, f"{opt}. {question.options[opt]}\n")
            text_widget.insert(tk.END, f"\n您的答案: {user_ans if user_ans else '(未答)'}\n")
            text_widget.insert(tk.END, f"正确答案: {correct_ans}\n")
        
        text_widget.config(state=tk.DISABLED)


def main():
    """主函数"""
    root = tk.Tk()
    app = ExamApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

