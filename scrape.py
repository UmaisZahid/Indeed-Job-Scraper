from bs4 import BeautifulSoup
import requests, json
import pandas as pd
from multiprocessing import Pool
from functools import partial


class scrape():

    def __init__(self):
        self.output_frame = None
        self.loading = False

    # Create base Indeed URL for all further scraping
    def create_url(parameters):
        # create base url for all further searches
        what = parameters['search_query'].replace(" ","+")
        where = parameters['location'].replace(" ","+")
        miles = parameters['miles']
        base_url = f"https://www.indeed.co.uk/jobs?q={what}&l={where}&radius={miles}"
        return base_url

    # Rate job based on parameters given
    def rate_job(j_title, j_soup, parameters):
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

    # Obtain details of the job (company, title, description etc.)
    def get_job_details(job, parameters):
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
        description, rating, keywords_present, title_keywords_present = scrape.rate_job(title, job_soup, parameters)

        return title, company, job_url, description, rating, keywords_present, title_keywords_present

    # Parallel version of old scraping routine. Run through MapPool using Multiprocessing library
    def parallel_scrape(parameters, url, page_num):

        # get page
        current_page = requests.get(url, timeout=5)
        page_soup = BeautifulSoup(current_page.content, "html.parser")
        page_output = []

        # Parse every job in page
        for job in page_soup.select(".jobsearch-SerpJobCard"):

            title, company, url, description, rating, keywords_present, title_keywords_present = scrape.get_job_details(
                job,
                parameters)

            page_output.append([rating, title, company, description, url, str(keywords_present),
                    str(title_keywords_present), page_num])

        return page_output

    # Primary function for obtaining scraped jobs
    def get_scrape(self,parameters):

        # Reset output and progress
        self.loading = True

        # Create base url for all further searches
        base_url = scrape.create_url(parameters)

        # Output list and frame
        output = []

        # Create pool of workers
        pool = Pool(min(parameters['pages'],5))

        # Dirty list comprehension to create argument list for pool workers
        pool_args = [(base_url + "&start=" + str(x * 10), x+1) if (x!=0) else (base_url,x+1)
                     for x in range(0,parameters['pages'])]

        # Get output of pool workers
        output = pool.starmap(partial(scrape.parallel_scrape,parameters), pool_args)
        output = [x for sublist in output for x in sublist]

        # Create dataframe from list of jobs
        df_output_frame = pd.DataFrame(
            output,
            columns=['Rating', 'Job Title', 'Company', 'Description', 'Job URL', 'Keywords Present', 'Title Keywords',
                     'Page Found']).sort_values(
            by='Rating', ascending=False).reset_index(drop=True)

        # Sort df by rating
        df_output_frame['Rating'] = df_output_frame['Rating'].round(decimals=3)
        df_output_frame = df_output_frame.drop_duplicates(subset=['Rating','Job Title','Company'])
        self.loading = False

        return df_output_frame

    # For outputting to excel locally
    def output_excel(df):
        with pd.ExcelWriter('/downloadable/Excel Output.xlsx', options={'strings_to_urls': False}) as writer:
            df.to_excel(writer, index=False)