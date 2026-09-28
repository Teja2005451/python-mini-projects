from pathlib import Path

code = r'''import ast
import math
import operator
import tkinter as tk


class SafeMath(ast.NodeVisitor):
    """Evaluate only approved mathematical expressions."""

    BIN_OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }

    UNARY_OPS = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def __init__(self, names, functions):
        self.names = names
        self.functions = functions

    def evaluate(self, expression):
        if len(expression) > 200:
            raise ValueError("Expression too long")
        tree = ast.parse(expression, mode="eval")
        return self.visit(tree.body)

    def visit_Constant(self, node):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("Only numbers are allowed")
        return node.value

    def visit_Name(self, node):
        if node.id not in self.names:
            raise ValueError(f"Unknown name: {node.id}")
        return self.names[node.id]

    def visit_BinOp(self, node):
        op_type = type(node.op)
        if op_type not in self.BIN_OPS:
            raise ValueError("Operator not allowed")

        left = self.visit(node.left)
        right = self.visit(node.right)

        if op_type is ast.Pow and abs(right) > 308:
            raise ValueError("Exponent too large")

        return self.BIN_OPS[op_type](left, right)

    def visit_UnaryOp(self, node):
        op_type = type(node.op)
        if op_type not in self.UNARY_OPS:
            raise ValueError("Unary operator not allowed")
        return self.UNARY_OPS[op_type](self.visit(node.operand))

    def visit_Call(self, node):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Function not allowed")

        name = node.func.id
        if name not in self.functions:
            raise ValueError(f"Unknown function: {name}")

        if node.keywords:
            raise ValueError("Keyword arguments are not allowed")

        args = [self.visit(arg) for arg in node.args]
        return self.functions[name](*args)

    def generic_visit(self, node):
        raise ValueError(f"Unsupported input: {type(node).__name__}")


class TejCalculatorPro:
    BG = "#0F172A"
    PANEL = "#111827"
    DISPLAY = "#020617"
    TEXT = "#F8FAFC"
    MUTED = "#94A3B8"
    NUMBER = "#1E293B"
    SCI = "#334155"
    OP = "#F59E0B"
    EQ = "#10B981"
    DANGER = "#EF4444"
    PURPLE = "#6366F1"

    def __init__(self, root):
        self.root = root
        self.root.title("Tej Scientific Calculator Pro")
        self.root.geometry("950x620")
        self.root.minsize(900, 580)
        self.root.configure(bg=self.BG)

        self.angle_mode = "DEG"
        self.memory = 0.0
        self.ans = 0.0
        self.history = []
        self.just_calculated = False

        self.expression = tk.StringVar()
        self.result = tk.StringVar(value="0")
        self.status = tk.StringVar(value="DEG   |   M = 0")

        self.build_ui()
        self.bind_keys()

    def build_ui(self):
        self.root.grid_columnconfigure(0, weight=3)
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        left = tk.Frame(self.root, bg=self.BG)
        left.grid(row=0, column=0, sticky="nsew", padx=(18, 9), pady=18)
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(2, weight=1)

        right = tk.Frame(self.root, bg=self.PANEL)
        right.grid(row=0, column=1, sticky="nsew", padx=(9, 18), pady=18)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=1)

        display = tk.Frame(left, bg=self.PANEL)
        display.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        display.grid_columnconfigure(0, weight=1)

        self.entry = tk.Entry(
            display,
            textvariable=self.expression,
            bg=self.DISPLAY,
            fg=self.TEXT,
            insertbackground=self.TEXT,
            font=("Segoe UI", 20),
            justify="right",
            relief="flat",
            bd=0,
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 4), ipady=8)

        tk.Label(
            display,
            textvariable=self.result,
            bg=self.PANEL,
            fg=self.TEXT,
            font=("Segoe UI", 33, "bold"),
            anchor="e",
        ).grid(row=1, column=0, sticky="ew", padx=15)

        tk.Label(
            display,
            textvariable=self.status,
            bg=self.PANEL,
            fg=self.MUTED,
            font=("Segoe UI", 10),
            anchor="e",
        ).grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 12))

        tools = tk.Frame(left, bg=self.BG)
        tools.grid(row=1, column=0, sticky="ew", pady=(0, 6))

        top_buttons = [
            ("DEG/RAD", self.toggle_angle, self.PURPLE),
            ("MC", self.memory_clear, self.SCI),
            ("MR", self.memory_recall, self.SCI),
            ("M+", self.memory_add, self.SCI),
            ("M−", self.memory_subtract, self.SCI),
            ("Copy", self.copy_result, self.SCI),
        ]

        for col, (text, command, color) in enumerate(top_buttons):
            tools.grid_columnconfigure(col, weight=1)
            self.button(tools, text, command, color, 11).grid(
                row=0, column=col, sticky="nsew", padx=3, pady=3, ipady=5
            )

        pad = tk.Frame(left, bg=self.BG)
        pad.grid(row=2, column=0, sticky="nsew")

        for row in range(6):
            pad.grid_rowconfigure(row, weight=1)
        for col in range(6):
            pad.grid_columnconfigure(col, weight=1)

        buttons = [
            [("(", lambda: self.insert("("), self.SCI),
             (")", lambda: self.insert(")"), self.SCI),
             ("%", self.percent, self.SCI),
             ("⌫", self.backspace, self.SCI),
             ("C", self.clear, self.DANGER),
             ("÷", lambda: self.insert_operator("/"), self.OP)],

            [("7", lambda: self.insert("7", True), self.NUMBER),
             ("8", lambda: self.insert("8", True), self.NUMBER),
             ("9", lambda: self.insert("9", True), self.NUMBER),
             ("×", lambda: self.insert_operator("*"), self.OP),
             ("sin", lambda: self.insert_function("sin"), self.SCI),
             ("cos", lambda: self.insert_function("cos"), self.SCI)],

            [("4", lambda: self.insert("4", True), self.NUMBER),
             ("5", lambda: self.insert("5", True), self.NUMBER),
             ("6", lambda: self.insert("6", True), self.NUMBER),
             ("−", lambda: self.insert_operator("-"), self.OP),
             ("tan", lambda: self.insert_function("tan"), self.SCI),
             ("log", lambda: self.insert_function("log"), self.SCI)],

            [("1", lambda: self.insert("1", True), self.NUMBER),
             ("2", lambda: self.insert("2", True), self.NUMBER),
             ("3", lambda: self.insert("3", True), self.NUMBER),
             ("+", lambda: self.insert_operator("+"), self.OP),
             ("ln", lambda: self.insert_function("ln"), self.SCI),
             ("√", self.sqrt, self.SCI)],

            [("±", self.toggle_sign, self.SCI),
             ("0", lambda: self.insert("0", True), self.NUMBER),
             (".", lambda: self.insert(".", True), self.NUMBER),
             ("=", self.calculate, self.EQ),
             ("x²", self.square, self.SCI),
             ("1/x", self.reciprocal, self.SCI)],

            [("π", lambda: self.insert("pi", True), self.PURPLE),
             ("e", lambda: self.insert("e", True), self.PURPLE),
             ("Ans", lambda: self.insert("ans", True), self.PURPLE),
             ("xʸ", lambda: self.insert_operator("**"), self.OP),
             ("n!", self.factorial, self.SCI),
             ("mod", lambda: self.insert_operator("%"), self.OP)],
        ]

        for r, row in enumerate(buttons):
            for c, (text, command, color) in enumerate(row):
                self.button(pad, text, command, color).grid(
                    row=r, column=c, sticky="nsew", padx=4, pady=4
                )

        tk.Label(
            right,
            text="History",
            bg=self.PANEL,
            fg=self.TEXT,
            font=("Segoe UI", 17, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))

        self.history_box = tk.Listbox(
            right,
            bg=self.DISPLAY,
            fg=self.TEXT,
            selectbackground=self.PURPLE,
            selectforeground="white",
            font=("Consolas", 11),
            relief="flat",
            bd=0,
            activestyle="none",
        )
        self.history_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=6)
        self.history_box.bind("<Double-Button-1>", self.use_history)

        self.button(
            right, "Clear History", self.clear_history, self.DANGER, 10
        ).grid(row=2, column=0, sticky="ew", padx=12, pady=12)

        self.entry.focus_set()

    def button(self, parent, text, command, color, font_size=14):
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg="white",
            activebackground=color,
            activeforeground="white",
            font=("Segoe UI", font_size, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
        )

    def insert(self, token, fresh=False):
        if self.just_calculated and fresh:
            self.expression.set("")

        self.just_calculated = False
        pos = self.entry.index(tk.INSERT)
        text = self.expression.get()
        self.expression.set(text[:pos] + token + text[pos:])
        self.entry.icursor(pos + len(token))
        self.entry.focus_set()

    def insert_operator(self, operator_text):
        if not self.expression.get().strip():
            if self.ans != 0:
                self.expression.set("ans")
            elif operator_text == "-":
                self.expression.set("-")
                return
            else:
                return

        self.just_calculated = False
        self.insert(operator_text)

    def insert_function(self, name):
        if self.just_calculated:
            self.expression.set("")
        self.insert(name + "(")

    def backspace(self):
        pos = self.entry.index(tk.INSERT)
        text = self.expression.get()
        if pos > 0:
            self.expression.set(text[:pos - 1] + text[pos:])
            self.entry.icursor(pos - 1)

    def clear(self):
        self.expression.set("")
        self.result.set("0")
        self.just_calculated = False
        self.entry.focus_set()

    def wrap_and_calculate(self, template):
        current = self.expression.get().strip() or "0"
        self.expression.set(template.format(current))
        self.calculate()

    def percent(self):
        self.wrap_and_calculate("({})/100")

    def square(self):
        self.wrap_and_calculate("({})**2")

    def sqrt(self):
        self.wrap_and_calculate("sqrt({})")

    def reciprocal(self):
        self.wrap_and_calculate("1/({})")

    def factorial(self):
        self.wrap_and_calculate("fact({})")

    def toggle_sign(self):
        self.wrap_and_calculate("-({})")

    def trig(self, func):
        def wrapped(x):
            if self.angle_mode == "DEG":
                x = math.radians(x)
            return func(x)
        return wrapped

    @staticmethod
    def safe_factorial(value):
        if isinstance(value, float) and not value.is_integer():
            raise ValueError("Factorial needs a whole number")

        value = int(value)

        if value < 0:
            raise ValueError("Factorial cannot use a negative number")

        if value > 100:
            raise ValueError("Factorial limit is 100")

        return math.factorial(value)

    def evaluator(self):
        return SafeMath(
            names={
                "pi": math.pi,
                "e": math.e,
                "ans": self.ans,
            },
            functions={
                "sin": self.trig(math.sin),
                "cos": self.trig(math.cos),
                "tan": self.trig(math.tan),
                "sqrt": math.sqrt,
                "log": math.log10,
                "ln": math.log,
                "fact": self.safe_factorial,
                "abs": abs,
            },
        )

    def evaluate(self, text):
        value = self.evaluator().evaluate(text)

        if isinstance(value, complex):
            raise ValueError("Complex results are not supported")

        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Invalid result")

        return value

    def calculate(self):
        text = self.expression.get().strip()
        if not text:
            return

        try:
            value = self.evaluate(text)
            answer = self.format_number(value)

            self.ans = value
            self.result.set(answer)
            self.expression.set(answer)
            self.just_calculated = True

            self.history.insert(0, (text, answer))
            self.history = self.history[:50]
            self.refresh_history()

        except ZeroDivisionError:
            self.result.set("Error: divide by zero")

        except (SyntaxError, ValueError, TypeError, OverflowError) as error:
            self.result.set("Error: " + (str(error) or "invalid expression"))

        self.entry.icursor(tk.END)
        self.entry.focus_set()

    @staticmethod
    def format_number(value):
        if isinstance(value, int):
            return str(value)

        if abs(value) < 1e-12:
            value = 0.0

        if abs(value) >= 1e12 or (0 < abs(value) < 1e-9):
            return f"{value:.10e}"

        return f"{value:.12g}"

    def current_value(self):
        text = self.expression.get().strip()
        return self.evaluate(text) if text else self.ans

    def memory_clear(self):
        self.memory = 0.0
        self.update_status()

    def memory_recall(self):
        self.expression.set(self.format_number(self.memory))
        self.just_calculated = False

    def memory_add(self):
        try:
            self.memory += self.current_value()
            self.update_status()
        except Exception as error:
            self.result.set("Error: " + str(error))

    def memory_subtract(self):
        try:
            self.memory -= self.current_value()
            self.update_status()
        except Exception as error:
            self.result.set("Error: " + str(error))

    def toggle_angle(self):
        self.angle_mode = "RAD" if self.angle_mode == "DEG" else "DEG"
        self.update_status()

    def update_status(self):
        self.status.set(
            f"{self.angle_mode}   |   M = {self.format_number(self.memory)}   |   F2: DEG/RAD"
        )

    def copy_result(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.result.get())
        self.root.update()

    def refresh_history(self):
        self.history_box.delete(0, tk.END)
        for expression, answer in self.history:
            self.history_box.insert(tk.END, f"{expression} = {answer}")

    def use_history(self, _event=None):
        selection = self.history_box.curselection()
        if selection:
            expression, _answer = self.history[selection[0]]
            self.expression.set(expression)
            self.just_calculated = False
            self.entry.focus_set()
            self.entry.icursor(tk.END)

    def clear_history(self):
        self.history.clear()
        self.refresh_history()

    def bind_keys(self):
        self.root.bind("<Return>", lambda _e: self.calculate())
        self.root.bind("<KP_Enter>", lambda _e: self.calculate())
        self.root.bind("<Escape>", lambda _e: self.clear())
        self.root.bind("<F2>", lambda _e: self.toggle_angle())
        self.root.bind("<Control-c>", lambda _e: self.copy_result())


if __name__ == "__main__":
    root = tk.Tk()
    TejCalculatorPro(root)
    root.mainloop()
'''

path = Path("/mnt/data/tej_calculator_pro.py")
path.write_text(code, encoding="utf-8")
print(f"Created: {path}")
