from bs4 import BeautifulSoup
import requests, json
import pandas as pd
import dash
from dash.dependencies import Input, Output


class scrape():

    def __init__(self):
        self.output_frame = None
        self.loading = False
        self.progress = 0

    def create_url(self,parameters):
        # create base url for all further searches
        what = parameters['search_query'].replace(" ","+")
        where = parameters['location'].replace(" ","+")
        miles = parameters['miles']
        base_url = f"https://www.indeed.co.uk/jobs?q={what}&l={where}&radius={miles}"
        return base_url


    def rate_job(self,j_title, j_soup, parameters):
        # rate job by keywords
        description = j_soup.find(id="jobDescriptionText").get_text()
        keywords = parameters['ordered_keywords']
        title_keywords = parameters['title_keywords']
        exclude_keywords = parameters['exclude_keywords']
        total_keywords = len(keywords) + len(title_keywords)
        keywords_present = []
        title_keywords_present = []
        rating = 0

        # Check for keyword, add value to rating depending on ranking
        for index, keyword in enumerate(keywords):
            if keyword in description:
                rating += len(keywords) - index
                keywords_present.append(keyword)

        # Check for title keywords
        for index, keyword in enumerate(title_keywords):
            if keyword in j_title:
                rating += total_keywords - index
                title_keywords_present.append(keyword)

        # Normalise rating
        rating = rating / sum(range(1, total_keywords + 1))

        # Check for excluded keywords
        for keyword in exclude_keywords:
            if keyword in j_title:
                rating = 0
                break

        return description, rating, keywords_present, title_keywords_present


    def get_job_details(self,job, parameters):
        # Get link and title
        job_url = job.find(class_='title').a['href']

        # Correct for truncated URLs
        job_url = "https://www.indeed.co.uk" + job_url if (job_url.startswith("/")) else job_url
        job_page = requests.get(job_url)
        job_soup = BeautifulSoup(job_page.content, 'html.parser')

        # Give URL after redirect (ads/analytics etc.)
        job_url = job_page.url

        # Get job title and company name
        title = job.find(class_='title').a['title']
        company = job_soup.find(class_="icl-u-lg-mr--sm").get_text()

        # Get description, rating and present keywords
        description, rating, keywords_present, title_keywords_present = self.rate_job(title, job_soup, parameters)

        return title, company, job_url, description, rating, keywords_present, title_keywords_present


    def get_scrape(self,parameters):

        # Reset output and progress
        output_frame = None
        progress = 0
        loading = True

        # Create base url for all further searches
        base_url = self.create_url(parameters)

        # Output list and frame
        output = []

        for x in range(0, parameters['pages']):
            if (x == 0):
                page_append = ""
            else:
                page_append = "&start=" + str(x * 10)

            # get page
            current_page = requests.get(base_url + page_append, timeout=5)
            page_soup = BeautifulSoup(current_page.content, "html.parser")

            for job in page_soup.select(".jobsearch-SerpJobCard"):
                title, company, url, description, rating, keywords_present, title_keywords_present = self.get_job_details(job,
                                                                                                                     parameters)
                output.append([rating, title, company, description, url, str(keywords_present),
                               str(title_keywords_present), x + 1])

            progress = x/parameters['pages']

        df_output_frame = pd.DataFrame(
            output,
            columns=['Rating', 'Job Title', 'Company', 'Description', 'Job URL', 'Keywords Present', 'Title Keywords',
                     'Page Found']).sort_values(
            by='Rating', ascending=False).reset_index(drop=True)

        df_output_frame['Rating'] = df_output_frame['Rating'].round(decimals=3)

        loading = False

        return df_output_frame

    def output_excel(df):
        with pd.ExcelWriter('/downloadable/Excel Output.xlsx', options={'strings_to_urls': False}) as writer:
            df.to_excel(writer, index=False)