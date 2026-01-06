import inquirer
from inquirer.themes import GreenPassion

def prompt_for_form_inputs() -> dict:
    questions = [
        inquirer.Text("form_name", message="Form Name (e.g. dental_patient_intake_v2)"),
        inquirer.Text("category", message="Category (Simpleform label)"),
    ]
    answers = inquirer.prompt(questions, theme=GreenPassion()) or {}

    form_name = (answers.get("form_name") or "").strip()
    category = (answers.get("category") or "").strip()

    if not form_name:
        raise ValueError("Form name is required")
    if not category:
        raise ValueError("Category is required")

    return {
        "form_name": form_name,
        "category": category,
    }
