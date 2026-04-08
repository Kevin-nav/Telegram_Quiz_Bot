We need to optimize how we get questions from the database using various methods and patterns.

1. Add an index to frequently used tables in the database
2. Utilize the redis cache to serve questions from cache too after the adaptive algorithm has picked up the questions. So we can use redis as our intermediate database until everything moves to the main database. Images too can and should also be cached into the redis database.
- How to implement the caching with the adaptive algorithm:
  - We cache all parts that do not change too much in the database that the adaptive algorithm reaches for all the time. like the number of questions, the names of the questions and all.
  - then we save more and more questions to cache for about 1 hour or more so the adaptive algorithm does not need to go to teh database to fetch all the questions needed for each session.
  - In terms of questions, we should make the questions in cache global so we don't refetch from the database when not needed to be done.
3. Precompute and store to the database things the admin platform will use, and then store what will change more frequently in the redis cache so we don't need to be straniing the database.



The main aim is to reduce the compute the database has to do in terms on amount of compute per query and also the number of queries tooo. we want to make sure it stays low as possible while still working for us.
