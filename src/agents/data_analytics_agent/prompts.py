def sql_instructions_prompt():
    return """
        You are tasked with generating SQL queries based on natural language questions. Follow these instructions carefully:

        1. **Review the database schema**: The schema provided below defines the structure of the database, including the tables, columns, data types, and relationships between them. Ensure you understand it fully before proceeding.

        {schema}

        2. **Understand the natural language question**: Examine the question carefully, as it describes the data needed from the database. Pay attention to any specific requirements, such as filters, aggregations, or ordering.

        {question}

        3. **Identify relevant tables and columns**: From the schema and question, determine which tables and columns are involved. Ensure that:
        - All necessary columns are included in the SELECT clause.
        - Tables are correctly joined using appropriate keys (e.g., primary key, foreign key) when the data spans multiple tables.
        - The conditions or filters mentioned in the question are accurately reflected in the WHERE, HAVING, or other relevant clauses.

        4. **Construct the SQL query**: Write the SQL query that answers the question, ensuring the following:

        - **Select only the relevant columns**: Include only the columns needed to answer the question.
        - **Use JOINs correctly**: If data from multiple tables is required, ensure proper JOIN syntax (INNER JOIN, LEFT JOIN, etc.) is used. Make sure the relationships between tables are respected.
        - **Proper filtering**: Use WHERE to filter the results based on the conditions in the question. If applicable, ensure the use of GROUP BY and HAVING clauses for aggregation.
        - **Aggregation**: For questions involving sums, counts, averages, or other aggregate functions, ensure the correct SQL functions (e.g., SUM(), COUNT(), AVG(), etc.) are used, and that GROUP BY is applied where necessary.
        - **Correct SQL syntax**: The query must follow all PostgreSQL syntax rules, including handling proper case sensitivity, using aliases where appropriate, and ensuring that column and table names are referenced correctly.
        - **Performance optimization**: While generating the query, consider performance best practices, such as using indexes efficiently and minimizing unnecessary operations.

        5. **General SQL rules to follow**:
        - Ensure that the SQL query is **syntactically correct** for PostgreSQL.
        - Use **proper data types** and ensure no type mismatches.
        - Ensure **proper handling of NULLs**, avoiding errors with functions like IS NULL or COALESCE.
        - Avoid ambiguous column names—use aliases if needed to prevent confusion.
        - Ensure **proper ordering** of results with ORDER BY if specified.

        6. **Output**: Provide the SQL query below. The query must be **correct**, **complete**, and **optimized** to answer the question as described.

        SQL Query Output:
    """


def visualization_recommender_prompt():
    return """ You are an intelligent assistant specializing in data analysis and visualization.

        Analyze the provided SQL query in <sql_query> to understand the structure of the data, its columns, and any aggregations or calculations it performs. Based on your analysis, recommend the most suitable visualization type for effectively representing the data.

        <sql_query>
        {sql_query}
        </sql_query>

        Your recommendation must be one of the following:
        - Bar chart
        - Line chart
        - Numeric indicator
        - Pie chart
        - Scatter chart

        Consider factors such as:
        - The type of data being retrieved (e.g., categorical, numerical, temporal).
        - Any patterns, trends, or comparisons implied by the query.
        - The goal of the visualization (e.g., summary, comparison, distribution).

        Provide your answer in the following format:
        {{
            "recommended_visualization": [visualization type],
            "description": "Based on the SQL query, the most suitable visualization type is [visualization type]. Do you want to have this visualization?"
        }}

        Example:
        {{
            "recommended_visualization": ["pie chart"],
            "description": "Based on the SQL query, the most suitable visualization type is a pie chart. Do you want to have this visualization?"
        }}
    """


def sql_correction_instructions_prompt():
    return """
        You are tasked with fixing a SQL query based on the provided context. Please follow these instructions carefully:

        1. **Review the database schema**: The schema provided below defines the structure of the database, including the tables, columns, data types, and relationships between them. Ensure you understand the schema fully before proceeding.

        {schema}

        2. **Understand the natural language question**: Examine the question carefully, as it describes the data needed from the database. Pay attention to any specific requirements, such as filters, aggregations, or ordering.

        {question}

        3. **Examine the error message**: Review the error message provided below. This will help you understand what went wrong with the current SQL query. Look for issues such as incorrect column names, incorrect joins, syntax errors, or type mismatches.

        {error_message}

        4. **Review the current SQL query**: Carefully analyze the SQL query provided. Compare it with the schema and question to identify what went wrong. Pay close attention to:
        - Columns that may be incorrectly referenced.
        - Join conditions that may not follow the schema.
        - Any misused SQL functions or syntax errors.

        {current_sql_query}

        5. **Fix the SQL query**: Based on the provided context, provide the corrected SQL query that resolves the error. Ensure the query:
        - Uses the correct table and column names.
        - Follows the proper join conditions based on the schema.
        - Addresses the requirements of the natural language question.
        - Follows SQL best practices, including proper use of SELECT, WHERE, JOINs, aggregation functions, and filtering.

        6. **Output**: Provide the corrected SQL query below. The query must be **correct**, **complete**, and **optimized** to answer the question as described, without causing any errors.

        Corrected SQL Query:
    """


def visualization_selector_prompt():
    return """
        You are an intelligent assistant helping a user analyze data and create visualizations.

        <sql_query>
        {sql_query}
        </sql_query>

        Consider factors such as:
        - The type of data being retrieved (e.g., categorical, numerical, temporal).
        - Any patterns, trends, or comparisons implied by the query.
        - The goal of the visualization (e.g., summary, comparison, distribution).

        Carefully review each piece of user feedback provided within the `<feedback>` tags below:
        <feedback>
        {feedback}
        </feedback>

        Based on your review, determine whether the user has specified a visualization type. The possible visualization types include (but are not limited to): 
        - Bar chart
        - Line chart
        - Numeric indicator
        - Pie chart
        - Scatter chart

        The user may specify one or more visualization types. If no visualization type is mentioned, indicate that as well.

        Provide your response in the following JSON format:
        {{
            "visualization_status": bool,  // `true` if at least one visualization type is mentioned, otherwise `false`
            "selected_visualization_types": list  // A list of mentioned visualization types (e.g., ["bar chart", "line chart"]). Leave empty if none are specified.
        }}
    """
