CREATE CONSTRAINT owner_key IF NOT EXISTS FOR (n:Owner) REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT brand_key IF NOT EXISTS FOR (n:Brand) REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT team_key IF NOT EXISTS FOR (n:Team) REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT agent_key IF NOT EXISTS FOR (n:Agent) REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT company_key IF NOT EXISTS FOR (n:Company) REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT person_key IF NOT EXISTS FOR (n:Person) REQUIRE n.key IS UNIQUE;
CREATE CONSTRAINT touch_id IF NOT EXISTS FOR (n:Touch) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT note_id IF NOT EXISTS FOR (n:Note) REQUIRE n.id IS UNIQUE;
CREATE INDEX company_country IF NOT EXISTS FOR (c:Company) ON (c.country);
CREATE VECTOR INDEX note_embedding IF NOT EXISTS
  FOR (n:Note) ON (n.embedding)
  OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}}
