# Created by hborcher at 12/15/2017
Feature: Tool Option Model
  # Enter feature description here

  Scenario: Dummy data
    Given we have two options called dummy and dummy2
    When we provide data to generate a Qt model
    Then we get a ToolOptionsModel object

  Scenario: Dummy2 data correct size
    Given we have two options called dummy and dummy2
    When we provide data to generate a Qt model
    Then it has 2 rows
    And it has 1 column

  Scenario: Dummy data has a option called my_option
    Given I have an options model with a single my_option
    When I ask for the display data of my_option
    Then the data returned is an empty string
    And the headerData is title case "My_Option"


  Scenario: Dummy data has a option called my_option but no changes are made
    Given I have an options model with a single my_option
    When I ask for the final data
    Then the results data is a dictionary
    And my_option as the only key
    And my_option has an empty string for its value

  Scenario: Dummy data has a option called my_option and changes are made to it
    Given I have an options model with a single my_option
    And I set the data to "my data"
    When I ask for the final data
    Then the results data is a dictionary
    And my_option as the only key
    And my_option has an "my data" its value
