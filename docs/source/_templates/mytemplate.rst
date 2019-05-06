{{ fullname | escape | underline}}

{% block module %}{% if module -%}
Subpackages
===========

{% for item in classes %}
    {% if not "__" in item %}
        {{ item }}
        {% if hasdoc(item) %}
        {% endif %}

    {% endif %}
{%- endfor %}


{% endif %}
{% endblock %}

{% for item in exceptions %}
  {{ item }}
{%- endfor %}

.. automodule:: {{ fullname }}




   {% block functions %}
   {% if functions %}
   .. rubric:: Functions

   .. autosummary::
   {% for item in functions %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block classes %}
   {% if classes %}
   .. rubric:: Classes

   .. autosummary::
   {% for item in classes %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}

   {% block exceptions %}
   {% if exceptions %}
   .. rubric:: Exceptions

   .. autosummary::
   {% for item in exceptions %}
      {{ item }}
   {%- endfor %}
   {% endif %}
   {% endblock %}
