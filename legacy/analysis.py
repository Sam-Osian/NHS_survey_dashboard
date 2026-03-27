#!/usr/bin/env python
# coding: utf-8

import os
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

class StaffSurvey:
    """
    A class to encapsulate the modular analysis workflow for NHS staff survey responses.

    This class processes survey responses for a specific staff group and for all-staff,
    including splitting responses, generating themes using LLMs, assigning themes, and
    generating summary tables. It also includes functionality to process CSV data via a
    class method that can optionally apply transformations.
    
    Different OpenAI models can be specified for theme generation, assignment, and splitting.
    """
    
    def __init__(self, staff_group, api_env_path='api.env',
                 theme_model="o1", assignment_model="gpt-4o-mini", splitting_model="gpt-4o-mini"):
        """
        Initialise the StaffSurvey instance.

        Parameters:
            staff_group (str): The specific staff group (e.g. "community care").
            api_env_path (str): Path to the .env file containing the OpenAI API key.
            theme_model (str): Default model to use for theme generation.
            assignment_model (str): Default model to use for theme assignment.
            splitting_model (str): Default model to use for splitting responses.
        """
        self.staff_group = staff_group
        
        # Load API key from the environment file.
        load_dotenv(api_env_path)
        openai_api_key = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=openai_api_key)
        
        # Default models for different tasks.
        self.theme_model = theme_model
        self.assignment_model = assignment_model
        self.splitting_model = splitting_model
        
        # Internal attributes.
        self.df = None               # Staff group responses.
        self.global_df = None        # All-staff responses.
        self.split_df = None         # Split staff group responses.
        self.labelled_staffgrp_df = None
        self.labelled_allstaff_df = None
        self.generated_staffgrp_themes = None
        self.generated_allstaff_themes = None
        
        # Summary tables.
        self.staffgrp_theme_table = None
        self.staffgrp_subtheme_table = None
        self.staffgrp_sentiment_table = None
        self.staffgrp_theme_sentiment_table = None
        self.allstaff_theme_table = None
        self.allstaff_subtheme_table = None
        self.allstaff_sentiment_table = None
        self.allstaff_theme_sentiment_table = None
        
        # Define the splitting prompt as a multi-line string.
        self.splitting_prompt = """
Your task is to split an open-text survey response from an NHS staff survey into segments by inserting new lines (\n) between distinct topics. Follow these rules strictly:

1. **Preserve Originality**: Do not rephrase, summarise, or alter the wording of the response in any way. Copy the text exactly as it appears, adding only \n characters where necessary.
2. **Split by Topic, Not Just Sentences**: Insert a \n character **only** when the respondent clearly transitions to a **new, distinct topic**. **Sentences discussing different aspects of the same issue should not be split.**
3. **Avoid Over-Splitting**: A topic **is not just a sentence—it is a concept.** Do not separate sentences just because they present different details. **If two sentences naturally flow together, they should remain together.**
4. **No Commentary**: Do not add headings, summaries, or any analysis. Your output should be the original text with \n characters added where appropriate.

---
### **Example 1**
--Original:  
"I feel unsupported by management. IT issues also delay my work. My colleagues are very helpful."

--Correct Output:  
"I feel unsupported by management.  

IT issues also delay my work.  

My colleagues are very helpful."

---
### **Example 2: When only SOME splitting is needed**
--Original:  
"The workload has been intense, and deadlines keep piling up. It feels like management doesn’t always see how much we’re juggling, which adds to the pressure. My team, though, has been fantastic—we support each other and keep things running even when it’s stressful."

--Correct Output:  
"The workload has been intense, and deadlines keep piling up. It feels like management doesn’t always see how much we’re juggling, which adds to the pressure.  

My team, though, has been fantastic—we support each other and keep things running even when it’s stressful."

---
### **Example 3: A Response That Should NOT Be Split at All**
--Original:  
"A number of clinical areas are short staffed and unable to recruit. The pressure placed on current staff can be unrealistic and makes the job exhausting and emotionally draining."

--Correct Output:  
"A number of clinical areas are short staffed and unable to recruit. The pressure placed on current staff can be unrealistic and makes the job exhausting and emotionally draining."

---
Now, apply these rules to the following response:
"""

    @classmethod
    def process_df(cls, df: pd.DataFrame, transform: bool = True) -> pd.DataFrame:
        """
        Process a raw DataFrame. If transform is True, drop the first two rows,
        reset the index, keep only the second column (renamed to 'comment'), and add an 'id' column.
        If transform is False, return the DataFrame as-is.

        Parameters:
            df (pd.DataFrame): The raw DataFrame.
            transform (bool): Whether to apply the transformations. Default is True.

        Returns:
            pd.DataFrame: The processed (or unaltered) DataFrame.
        """
        if transform:
            df = df.drop([0, 1], axis='index')
            df = df.reset_index(drop=True)
            df = df.iloc[:, [1]]
            df.columns = ['comment']
            df.insert(0, 'id', range(1, len(df) + 1))
        return df

    # ----------------------- Data Input Methods -----------------------
    def read_staffgrp(self, df: pd.DataFrame, transform: bool = True):
        """
        Process and store a DataFrame containing specific staff group responses.

        Parameters:
            df (pd.DataFrame): Raw DataFrame for the staff group.
            transform (bool): Whether to apply data transformations. Default is True.
        """
        self.df = StaffSurvey.process_df(df, transform)
        print("Staff group data loaded successfully.")

    def read_allstaff(self, df: pd.DataFrame, transform: bool = True):
        """
        Process and store a DataFrame containing all-staff responses.

        Parameters:
            df (pd.DataFrame): Raw DataFrame for all staff.
            transform (bool): Whether to apply data transformations. Default is True.
        """
        self.global_df = StaffSurvey.process_df(df, transform)
        print("All-staff data loaded successfully.")

    # ----------------------- Splitting Methods -----------------------
    def get_responses(self, df, text_col, prompt, print_output=False, model=None):
        """
        Call the OpenAI API for each row in a DataFrame with the given prompt.

        Parameters:
            df (pd.DataFrame): The DataFrame containing the text.
            text_col (str): The column name containing the text.
            prompt (str): The prompt to send to the LLM.
            print_output (bool): If True, print each original text and response.
            model (str): (Optional) Model to use; if not provided, defaults to assignment_model.

        Returns:
            List[str]: A list of responses from the LLM.
        """
        if model is None:
            model = self.assignment_model
        responses = []
        for index, row in df.iterrows():
            content = row[text_col]
            dynamic_prompt = prompt + content
            if print_output:
                print(f"***\n\n--Original Text:\n{content}")
            try:
                completion = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": dynamic_prompt}
                    ],
                    temperature=0
                )
                response = completion.choices[0].message.content
            except Exception as e:
                print(f"Error at index {index}: {e}")
                response = None
            if response:
                if print_output:
                    print(f"\n\n--Response:\n{response}")
                responses.append(response)
        return responses

    def split_comments(self, df, split_col="split_comment"):
        """
        Split the text in the specified column by double newlines.

        Parameters:
            df (pd.DataFrame): DataFrame with a column of text to split.
            split_col (str): Column name that contains the text to split.

        Returns:
            pd.DataFrame: A new DataFrame where each split segment is a separate row.
        """
        new_rows = []
        for _, row in df.iterrows():
            if pd.notna(row[split_col]):
                comment_splits = row[split_col].split("\n\n")
                for split in comment_splits:
                    split = split.strip()
                    if split:
                        new_rows.append({'id': row['id'], 'comment': split})
        return pd.DataFrame(new_rows)

    def split(self, print_sample=False, model=None):
        """
        Split the staff group survey responses using the splitting prompt.
        The results are stored in self.split_df.

        Parameters:
            print_sample (bool): If True, print responses for a sample.
            model (str): (Optional) Model to use for splitting; defaults to splitting_model.
        """
        if self.df is None:
            print("Error: Staff group data not loaded. Call read_staffgrp() first.")
            return
        if model is None:
            model = self.splitting_model
        sample = self.df.iloc[0:10].copy()
        sample['split_comment'] = self.get_responses(sample, 'comment', self.splitting_prompt, print_output=print_sample, model=model)
        full_df = self.df.copy()
        full_df['split_comment'] = self.get_responses(full_df, 'comment', self.splitting_prompt, print_output=False, model=model)
        self.split_df = self.split_comments(full_df, "split_comment")
        print("Staff group comments split successfully.")

    # ----------------------- Theme Generation Methods -----------------------
    def generate_staffgrp_themes(self, print_output=False, model=None):
        """
        Generate a list of themes and subthemes for the staff group using an OpenAI API call.
        The generated themes are stored in self.generated_staffgrp_themes.

        Parameters:
            print_output (bool): If True, print the generated themes.
            model (str): (Optional) Model to use for theme generation; defaults to theme_model.
        """
        if model is None:
            model = self.theme_model
        staffgrp_theme_prompt = f"""
Generate a list of themes and subthemes for an NHS staff survey for the staff group "{self.staff_group}".
Output the list in markdown format with each theme as a header and its subthemes as bullet points.
Do not include any additional commentary.
"""
        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": staffgrp_theme_prompt}
                ],
                temperature=0
            )
            self.generated_staffgrp_themes = completion.choices[0].message.content
        except Exception as e:
            print("Error generating staff group theme list:", e)
            self.generated_staffgrp_themes = "Error generating staff group theme list."
        if print_output:
            print("Generated Staff Group Themes and Subthemes:")
            print(self.generated_staffgrp_themes)

    def generate_allstaff_themes(self, print_output=False, model=None):
        """
        Generate a master list of themes and subthemes for all-staff responses using an OpenAI API call.
        The generated themes are stored in self.generated_allstaff_themes.

        Parameters:
            print_output (bool): If True, print the generated themes.
            model (str): (Optional) Model to use for theme generation; defaults to theme_model.
        """
        if model is None:
            model = self.theme_model
        allstaff_theme_prompt = """
Generate a list of global themes and subthemes for an NHS staff survey for all-staff responses.
Output the list in markdown format with each theme as a header and its subthemes as bullet points.
Do not include any additional commentary.
"""
        try:
            completion = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": allstaff_theme_prompt}
                ],
                temperature=0
            )
            self.generated_allstaff_themes = completion.choices[0].message.content
        except Exception as e:
            print("Error generating all-staff theme list:", e)
            self.generated_allstaff_themes = "Error generating all-staff theme list."
        if print_output:
            print("Generated All-Staff Themes and Subthemes:")
            print(self.generated_allstaff_themes)

    # ----------------------- Theme Assignment Methods -----------------------
    def get_labelling_prompt(self, staffgrp_themes, allstaff_themes):
        """
        Construct the labelling prompt by incorporating both the staff group and all-staff theme lists.

        Parameters:
            staffgrp_themes (str): The generated themes for the staff group.
            allstaff_themes (str): The master themes for all-staff.

        Returns:
            str: The complete labelling prompt.
        """
        labelling_prompt = f"""
You will be given a brief snippet of text from an NHS staff survey. Your goal is to return both a theme from the combined list below and a sentiment (either: positive, negative, or neutral).

Below is the master (all-staff) list of themes and subthemes:
{allstaff_themes}

Below is the staff group list of themes and subthemes for the {self.staff_group} staff group:
{staffgrp_themes}

Please format your response as follows: [theme//subtheme//sentiment]
Do not add headings, summaries, or any analysis. Your response should be as outlined above only.
"""
        return labelling_prompt

    def assign_staffgrp_themes(self, print_sample=False, allstaff_themes=None, model=None):
        """
        Label the split staff group responses using a combined prompt that incorporates both 
        the staff group and all-staff theme lists. The results are stored in self.labelled_staffgrp_df.

        Parameters:
            print_sample (bool): If True, print sample responses.
            allstaff_themes (str): (Optional) A pre-generated all-staff theme list to use.
            model (str): (Optional) Model to use for assignment; defaults to assignment_model.
        """
        if not self.generated_staffgrp_themes:
            print("Error: Staff group themes not generated. Call generate_staffgrp_themes() first.")
            return
        if allstaff_themes is None:
            if not self.generated_allstaff_themes:
                print("Error: All-staff themes not generated. Call generate_allstaff_themes() first.")
                return
            else:
                allstaff_themes = self.generated_allstaff_themes
        if model is None:
            model = self.assignment_model
        labelling_prompt = self.get_labelling_prompt(self.generated_staffgrp_themes, allstaff_themes)
        self.split_df['assignment'] = self.get_responses(self.split_df, 'comment', labelling_prompt, print_output=False, model=model)
        split_results = self.split_df['assignment'].str.split('//')
        self.split_df['split_length'] = split_results.apply(len)
        invalid_rows = self.split_df[self.split_df['split_length'] != 3]
        if not invalid_rows.empty:
            print("Invalid rows in staff group assignment:")
            print(invalid_rows.to_string(index=False))
        self.labelled_staffgrp_df = self.split_df[self.split_df['split_length'] == 3].copy()
        self.labelled_staffgrp_df[['theme', 'subtheme', 'sentiment']] = pd.DataFrame(
            self.labelled_staffgrp_df['assignment'].str.split('//').tolist(),
            index=self.labelled_staffgrp_df.index
        )
        self.labelled_staffgrp_df = self.labelled_staffgrp_df.drop(columns=['split_length', 'assignment'])
        print("Staff group themes assigned successfully.")

    def assign_allstaff_themes(self, print_sample=False, model=None):
        """
        Label the all-staff responses using the all-staff theme list.
        The results are stored in self.labelled_allstaff_df.

        Parameters:
            print_sample (bool): If True, print sample responses.
            model (str): (Optional) Model to use for assignment; defaults to assignment_model.
        """
        if self.global_df is None:
            print("Error: All-staff data not loaded. Call read_allstaff() first.")
            return
        if model is None:
            model = self.assignment_model
        sample = self.global_df.iloc[0:10].copy()
        sample['split_comment'] = self.get_responses(sample, 'comment', self.splitting_prompt, print_output=print_sample, model=self.splitting_model)
        full_df = self.global_df.copy()
        full_df['split_comment'] = self.get_responses(full_df, 'comment', self.splitting_prompt, print_output=False, model=self.splitting_model)
        allstaff_split_df = self.split_comments(full_df, "split_comment")
        if not self.generated_allstaff_themes:
            print("Error: All-staff themes not generated. Call generate_allstaff_themes() first.")
            return
        labelling_prompt = f"""
You will be given a brief snippet of text from an NHS staff survey. Your goal is to return a theme from the list below and a sentiment (either: positive, negative, or neutral).

Below is the master (all-staff) list of themes and subthemes:
{self.generated_allstaff_themes}

Please format your response as follows: [theme//subtheme//sentiment]
Do not add headings, summaries, or any analysis. Your response should be as outlined above only.
"""
        allstaff_split_df['assignment'] = self.get_responses(allstaff_split_df, 'comment', labelling_prompt, print_output=False, model=model)
        split_results = allstaff_split_df['assignment'].str.split('//')
        allstaff_split_df['split_length'] = split_results.apply(len)
        invalid_rows = allstaff_split_df[allstaff_split_df['split_length'] != 3]
        if not invalid_rows.empty:
            print("Invalid rows in all-staff assignment:")
            print(invalid_rows.to_string(index=False))
        self.labelled_allstaff_df = allstaff_split_df[allstaff_split_df['split_length'] == 3].copy()
        self.labelled_allstaff_df[['theme', 'subtheme', 'sentiment']] = pd.DataFrame(
            self.labelled_allstaff_df['assignment'].str.split('//').tolist(),
            index=self.labelled_allstaff_df.index
        )
        self.labelled_allstaff_df = self.labelled_allstaff_df.drop(columns=['split_length', 'assignment'])
        print("All-staff themes assigned successfully.")

    # ----------------------- Analysis Methods -----------------------
    def analyse_staffgrp(self, print_sample=False):
        """
        Generate summary tables from the labelled staff group responses.
        The resulting tables are stored in internal attributes.

        Parameters:
            print_sample (bool): If True, print sample output of the tables.
        """
        if self.labelled_staffgrp_df is None:
            print("Error: Staff group themes not assigned. Call assign_staffgrp_themes() first.")
            return
        total_count = len(self.labelled_staffgrp_df)
        self.staffgrp_theme_table = self.labelled_staffgrp_df.groupby("theme")["id"].count().reset_index()
        self.staffgrp_theme_table.columns = ["Theme", "Count"]
        self.staffgrp_theme_table["Percentage"] = (self.staffgrp_theme_table["Count"] / total_count * 100).round(1)
        
        self.staffgrp_subtheme_table = self.labelled_staffgrp_df.groupby(["theme", "subtheme"])["id"].count().reset_index()
        self.staffgrp_subtheme_table.columns = ["Theme", "Subtheme", "Count"]
        self.staffgrp_subtheme_table["Percentage"] = (self.staffgrp_subtheme_table["Count"] / total_count * 100).round(1)
        
        self.staffgrp_sentiment_table = self.labelled_staffgrp_df.groupby("sentiment")["id"].count().reset_index()
        self.staffgrp_sentiment_table.columns = ["Sentiment", "Count"]
        self.staffgrp_sentiment_table["Percentage"] = (self.staffgrp_sentiment_table["Count"] / total_count * 100).round(1)
        
        self.staffgrp_theme_sentiment_table = self.labelled_staffgrp_df.groupby(["theme", "sentiment"])["id"].count().reset_index()
        self.staffgrp_theme_sentiment_table.columns = ["Theme", "Sentiment", "Count"]
        self.staffgrp_theme_sentiment_table["Percentage"] = (self.staffgrp_theme_sentiment_table["Count"] / total_count * 100).round(1)
        
        print("\n# Staff Group Themes Count and Percentage")
        print(self.staffgrp_theme_table.to_markdown(index=False))
        print("\n# Staff Group Themes and Subthemes Count and Percentage")
        print(self.staffgrp_subtheme_table.to_markdown(index=False))
        print("\n# Staff Group Sentiment Count and Percentage")
        print(self.staffgrp_sentiment_table.to_markdown(index=False))
        print("\n# Staff Group Themes by Sentiment Count and Percentage")
        print(self.staffgrp_theme_sentiment_table.to_markdown(index=False))
        print("Staff group analysis completed.")

    def analyse_allstaff(self, print_sample=False):
        """
        Generate summary tables from the labelled all-staff responses.
        The resulting tables are stored in internal attributes.

        Parameters:
            print_sample (bool): If True, print sample output of the tables.
        """
        if self.labelled_allstaff_df is None:
            print("Error: All-staff themes not assigned. Call assign_allstaff_themes() first.")
            return
        total_count = len(self.labelled_allstaff_df)
        self.allstaff_theme_table = self.labelled_allstaff_df.groupby("theme")["id"].count().reset_index()
        self.allstaff_theme_table.columns = ["Theme", "Count"]
        self.allstaff_theme_table["Percentage"] = (self.allstaff_theme_table["Count"] / total_count * 100).round(1)
        
        self.allstaff_subtheme_table = self.labelled_allstaff_df.groupby(["theme", "subtheme"])["id"].count().reset_index()
        self.allstaff_subtheme_table.columns = ["Theme", "Subtheme", "Count"]
        self.allstaff_subtheme_table["Percentage"] = (self.allstaff_subtheme_table["Count"] / total_count * 100).round(1)
        
        self.allstaff_sentiment_table = self.labelled_allstaff_df.groupby("sentiment")["id"].count().reset_index()
        self.allstaff_sentiment_table.columns = ["Sentiment", "Count"]
        self.allstaff_sentiment_table["Percentage"] = (self.allstaff_sentiment_table["Count"] / total_count * 100).round(1)
        
        self.allstaff_theme_sentiment_table = self.labelled_allstaff_df.groupby(["theme", "sentiment"])["id"].count().reset_index()
        self.allstaff_theme_sentiment_table.columns = ["Theme", "Sentiment", "Count"]
        self.allstaff_theme_sentiment_table["Percentage"] = (self.allstaff_theme_sentiment_table["Count"] / total_count * 100).round(1)
        
        print("\n# All-Staff Themes Count and Percentage")
        print(self.allstaff_theme_table.to_markdown(index=False))
        print("\n# All-Staff Themes and Subthemes Count and Percentage")
        print(self.allstaff_subtheme_table.to_markdown(index=False))
        print("\n# All-Staff Sentiment Count and Percentage")
        print(self.allstaff_sentiment_table.to_markdown(index=False))
        print("\n# All-Staff Themes by Sentiment Count and Percentage")
        print(self.allstaff_theme_sentiment_table.to_markdown(index=False))
        print("All-staff analysis completed.")


# ----------------------- Example Modular Usage -----------------------
if __name__ == "__main__":
    """
    Example usage:
      - "data/community_care.csv" contains responses for a specific staff group.
      - "data/all_staff.csv" contains responses from all staff.
      
    The master (all-staff) theme list is generated once and then passed to each staff group analysis.
    """
    # Generate the master (all-staff) theme list.
    allstaff_df = pd.read_csv("data/all_staff.csv", encoding="cp1252")
    allstaff_analysis = StaffSurvey(staff_group="all_staff")
    allstaff_analysis.read_allstaff(allstaff_df)
    allstaff_analysis.generate_allstaff_themes(print_output=True, model="o1")
    master_themes = allstaff_analysis.generated_allstaff_themes
    
    # Process a specific staff group (e.g. community care).
    staffgrp_df = pd.read_csv("data/community_care.csv", encoding="cp1252")
    community_care_analysis = StaffSurvey(staff_group="community care")
    community_care_analysis.read_staffgrp(staffgrp_df)
    community_care_analysis.split(print_sample=True, model="gpt-4o-mini")
    community_care_analysis.generate_staffgrp_themes(print_output=True, model="o1")
    # Pass the pre-generated master themes when assigning staff group themes.
    community_care_analysis.assign_staffgrp_themes(print_sample=True, allstaff_themes=master_themes, model="gpt-4o-mini")
    community_care_analysis.analyse_staffgrp(print_sample=True)
    
    # Similar steps can be repeated for other staff groups while reusing the same master themes.
