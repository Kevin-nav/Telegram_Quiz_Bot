We need to optimize how we get questions from the database using various methods and patterns.

1. Add an index to frequently used tables in the database
2. Use Redis as a hot cache for the adaptive selector and runtime state, not as an intermediate primary database. Keep Postgres canonical and keep binary images in R2/CDN.
- How to implement the caching with the adaptive algorithm:
  - Cache a lightweight per-course question manifest for selector fields such as question key, topic, difficulty, band, and variant pointers.
  - Cache a per-learner selector snapshot with attempted IDs, attempt summaries, last correct timestamps, and SRS state so quiz start does not have to rescan raw attempts.
  - Fetch full canonical question rows only for the selected question keys after the algorithm chooses them.
3. Precompute and store in Postgres the summaries the admin platform will use, then let Redis cache the latest hot payloads with stale-while-revalidate behavior.

The main aim is to reduce the compute the database has to do, both in amount of work per query and in the number of queries, while keeping the system correct and easy to rebuild if Redis is lost.
