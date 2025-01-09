def sql_to_excel_converter_prompt(content: str) -> str:
    prompt = f"""
    Analyze the SQL query within <query> tags and return a JSON object following this exact structure without missing any column or details of sql query:
    {{
        "Table Name": "string",
        "Columns": [
            {{
                "Column Name": "string",
                "Data Type": "string",
                "Constraints": "string or None",
                "Description": "string or No description",
                "Default Value": "string or None"
            }}
        ],
        "Primary Key": "string or Not defined",
        "Foreign Keys": [
            {{
                "Column Name": "string",
                "Referenced Table": "string",
                "Referenced Column": "string",
                "On Delete/Update Action": "string or None"
            }}
        ],
        "Additional Information": "string",
        "Relationships": "string",
        "Constraints and Rules": "string",
        "Potential Implications": "string"
    }}

    Rules:
    1. Extract only information explicitly defined in the SQL
    2. Return valid JSON only
    3. Include all columns with their complete details
    4. Use "None" for missing optional values
    5. Don't make assumptions about undefined information
    6. If you miss single column or any detail, I will be facing error. So, try to include all details.

    <query>{content}</query>
    """
    return prompt
