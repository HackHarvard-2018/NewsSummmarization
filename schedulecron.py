from crontab import CronTab

my_cron = CronTab(user='terencelim')
job = my_cron.new(command='python /Users/terencelim/Documents/NewsSummmarization/scraperscripts/techcrunch_scraper.py')
job.minute.every(1)

my_cron.write()
