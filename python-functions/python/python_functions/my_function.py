from functions.api import function, Date, Integer, String
from datetime import timedelta
from typing import Optional


# You can test your code in real time using the Live Preview feature, located in the
# Functions tab at the bottom of the screen.


@function
def example_addition_function(a: int, b: int) -> str:
    return f"The sum of {a} and {b} is {a + b}."


@function
def example_date_function(date: Date, days_ahead: Integer = 3) -> String:
    return f"{days_ahead} days after {date} is {date + timedelta(days=days_ahead)}."


@function
def example_fibonacci_function(n: Optional[int] = None) -> list[int]:
    n = n if n is not None else 10
    a, b, seq = 0, 1, []
    for i in range(n):
        seq.append(a)
        a, b = b, a + b
    return seq


# Using the generated Python OSDK (note: "Aircraft" may not exist in your ontology. Import
# your object types from the Resource imports sidebar, and an OSDK will be generated for you)

# from functions.api import OntologyEdit
# from ontology_sdk import FoundryClient
# from ontology_sdk.ontology.objects import Aircraft, AircraftPart
# from ontology_sdk.ontology.object_sets import AircraftObjectSet, AircraftPartObjectSet


# @function
# def aircraft_input_example(aircraft: Aircraft) -> str:
#     return f"{aircraft.brand} aircraft, holds {aircraft.capacity} passengers"


# @function
# def aircraft_search_example() -> AircraftObjectSet:
#     client = FoundryClient()
#     high_capacity = client.ontology.objects.Aircraft.where(Aircraft.object_type.capacity > 300)
#     high_speed = client.ontology.objects.Aircraft.where(Aircraft.object_type.speed > 500)
#     expensive = client.ontology.objects.Aircraft.where(Aircraft.object_type.price > 200_000_000)
#     return high_capacity.intersect(high_speed).subtract(expensive)


# @function
# def aircraft_links_example(aircraft: Aircraft) -> list[AircraftPart]:
#     return list(aircraft.parts.iterate())


# @function
# def aircraft_search_around_example(aircraft_set: AircraftObjectSet) -> AircraftPartObjectSet:
#     return aircraft_set.search_around_parts()


# @function(edits=[Aircraft])
# def edit_aircraft_example(aircraft: Aircraft, updated_capacity: int) -> list[OntologyEdit]:
#     edits = FoundryClient().ontology.edits()
#     edits.objects.Aircraft.edit(aircraft).capacity = updated_capacity
#     return edits.get_edits()
