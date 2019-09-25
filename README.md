# What is this and how does it work?

### What is this?

A bot that scrapes Indeed and parses job descriptions to return to you an ordered list of jobs based on your preferences.

### How it works?

You provide a set of standard input parameters: 
- **search query**
- **location**
- **mile/range**

in addition to two non-standard paramaters: 
- **ordered_keywords**: Job roles are rated based on this ordered list. This is a list of keywords to search for in job descriptions provided in order of preference. 
- **exclude_keywords**: A list of keywords to search for in a job _title_ which renders the rating of that job zero. E.g. if you really hate roles as a recruiter you would include: "Recruitment" or "Headhunter"

The web scraper searches through 100 pages of indeed job listings with those paramaters and returns a dataframe containing all the listings ordered by the "rating" metric based on the ordered list of keywords.

You can also then output this dataframe as an excel sheet for convenience. 

_note_: Excel hyperlinks are limited to 255 characters. Many of the job URLs exceed this limit, as such they are formatted as strings in the excel output. 

### Example Dataframe

<img src="img/Pandas_Output.PNG">

### Example Excel Output

<img src="img/Example_Output.PNG">