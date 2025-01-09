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
