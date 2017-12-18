# Created by hborcher at 12/15/2017
Feature: Tool Option Model with feature options
  # Enter feature description here

  Scenario: Dummy data with ToolOptions
    Given we have two ToolOptions called dummy and dummy2
    When we provide data to generate a Qt model options model 2
    Then we get a ToolOptionsModel2 object

  Scenario: Dummy2 data with ToolOptions correct size
    Given we have two ToolOptions called dummy and dummy2
    When we provide data to generate a Qt model options model 2
    Then we get a ToolOptionsModel2 object
    Then the model has 2 rows
    And the model has 1 column

  Scenario: Dummy data with ToolOptions has a option called my_option
    Given I have an options model with ToolOptions 2 with a single my_option
    When I ask for the display data of my_option
    Then the data returned is an empty string
    And the headerData is title case "My_Option"


  Scenario: Dummy data with ToolOptions has a option called my_option but no changes are made
    Given I have an options model with ToolOptions 2 with a single my_option
    When I ask for the final data
    Then the results data is a dictionary
    And my_option as the only key
    And my_option has an empty string for its value

  Scenario: Dummy data with ToolOptions has a option called my_option and changes are made to it
    Given I have an options model with ToolOptions 2 with a single my_option
    And I set the data to "my data"
    When I ask for the final data
    Then the results data is a dictionary
    And my_option as the only key
    And my_option has an "my data" its value
