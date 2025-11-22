MVP(Minimal Viable Product) : 

accept data from admin like slots, students, subjects, assignments etc  and store it ina database
use the constraint solver to generate timetables and store them
preview the timetables option and select one
maybe restapi for future ui

used : 
language : python
logic : google ortools cp-sat
database: sqlite with Object-Relational Mapping (ORM) : sqlalchemy
framework : fastapi
sqlcodegen for automapping of database to generate orm models for sqlalchemy