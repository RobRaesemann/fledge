/*
 * Fledge
 *
 * Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */

#include <string>
#include <sstream>
#include <iomanip>
#include <cfloat>
#include <vector>
#include <stdexcept>
#include <logger.h>
#include <datapoint.h>

 /**
 * Return the value as a string
 *
 * @return	String representing the DatapointValue object
 */
std::string DatapointValue::toString() const
{
	std::ostringstream ss;

	switch (m_type)
	{
	case T_INTEGER:
		ss << m_value.i;
		return ss.str();
	case T_FLOAT:
		{
			char tmpBuffer[100];
			std::string s;

			snprintf(tmpBuffer, sizeof(tmpBuffer), "%.10f", m_value.f);
			s= tmpBuffer;

			// remove trailing 0's
			if (s[s.size()-1]== '0') {
				s.erase(s.find_last_not_of('0') + 1, std::string::npos);

				// add '0' i
				if (s[s.size()-1]== '.')
					s.append("0");

			}

			return s;
		}
	case T_FLOAT_ARRAY:
		ss << "[";
		for (auto it = m_value.a->begin();
		     it != m_value.a->end();
		     ++it)
		{
			if (it != m_value.a->begin())
			{
				ss << ", ";
			}
			ss << *it;
		}
		ss << "]";
		return ss.str();
	case T_DP_DICT:
	case T_DP_LIST:
		ss << ((m_type==T_DP_DICT)?'{':'[');
		for (auto it = m_value.dpa->begin(); // std::vector<Datapoint *>*	dpa;
		     it != m_value.dpa->end();
		     ++it)
		{
			if (it != m_value.dpa->begin())
			{
				ss << ", ";
			}
			ss << ((m_type==T_DP_DICT)?(*it)->toJSONProperty():(*it)->getData().toString());
		}
		ss << ((m_type==T_DP_DICT)?'}':']');
		return ss.str();
	case T_STRING:
	default:
		ss << "\"";
		ss << escape(*m_value.str);
		ss << "\"";
		return ss.str();
	}
}

/**
 * Delete the DatapointValue along with possibly nested Datapoint objects
 */
void DatapointValue::deleteNestedDPV()
{
	if (m_type == T_STRING)
	{
		delete m_value.str;
		m_value.str = NULL;
	}
	else if (m_type == T_FLOAT_ARRAY)
	{
		delete m_value.a;
		m_value.a = NULL;
	}
	else if (m_type == T_DP_DICT ||
		 m_type == T_DP_LIST)
	{
		if (m_value.dpa) {
			for (auto it = m_value.dpa->begin();
				 it != m_value.dpa->end();
				 ++it)
			{
				// Call DatapointValue destructor
				delete(*it);
			}

			// Remove vector pointer
			delete m_value.dpa;
			m_value.dpa = NULL;
		}
	}
}

/**
 * DatapointValue class destructor
 */
DatapointValue::~DatapointValue()
{
	// Remove memory allocated by datapoints
	// along with possibly nested Datapoint objects
	deleteNestedDPV();
}

/**
 * Copy constructor
 */
DatapointValue::DatapointValue(const DatapointValue& obj)
{
	m_type = obj.m_type;
	switch (m_type)
	{
		case T_STRING:
			m_value.str = new std::string(*(obj.m_value.str));
			if (!m_value.str)
			{
				Logger::getLogger()->error("Failed to allocate string in datapoint value copy constructor");
				throw std::runtime_error("Failed to allocate string in datapoint value copy constructor");
			}
			break;
		case T_FLOAT_ARRAY:
			m_value.a = new std::vector<double>(*(obj.m_value.a));
			if (!m_value.a)
			{
				Logger::getLogger()->error("Failed to allocate float array in datapoint value copy constructor");
				throw std::runtime_error("Failed to allocate float array in datapoint value copy constructor");
			}
			break;
		case T_DP_DICT:
		case T_DP_LIST:
			m_value.dpa = new std::vector<Datapoint*>();
			for (auto it = obj.m_value.dpa->begin();
				it != obj.m_value.dpa->end();
				++it)
			{
				Datapoint *d = *it;
				if (d)
				{
					// Add new allocated datapoint to the vector
					// using copy constructor
					Datapoint *tmp = new Datapoint(*d);
					if (!tmp)
					{
						Logger::getLogger()->error("Failed to allocate datapoint for nested datapoint value in copy constructor");
						throw std::runtime_error("Failed to allocate datapoint for nested datapoint value in copy constructor");
					}
					m_value.dpa->push_back(tmp);
				}
				else
				{
					Logger::getLogger()->error("NULL datapoint found in nested data point value in copy constructor");
					throw std::runtime_error("NULL datapoint found in nested data point value in copy constructor");
				}
			}

			break;
		default:
			m_value = obj.m_value;
			break;
	}
}

/**
 * Assignment Operator
 */
DatapointValue& DatapointValue::operator=(const DatapointValue& rhs)
{
	if (m_type == T_STRING)
	{
		// Remove previous value
		delete m_value.str;
	}
	if (m_type == T_FLOAT_ARRAY)
	{
		// Remove previous value
		delete m_value.a;
	}
	if (m_type == T_DP_DICT || m_type == T_DP_LIST)
	{
		// Remove previous value
		delete m_value.dpa;
	}

	m_type = rhs.m_type;

	switch (m_type)
	{
	case T_STRING:
		m_value.str = new std::string(*(rhs.m_value.str));
		break;
	case T_FLOAT_ARRAY:
		m_value.a = new std::vector<double>(*(rhs.m_value.a));
		break;
	case T_DP_DICT:
	case T_DP_LIST:
		m_value.dpa = new std::vector<Datapoint*>();
		for (auto it = rhs.m_value.dpa->begin();
			it != rhs.m_value.dpa->end();
			++it)
		{
			Datapoint *d = *it;
			if (d)
			{
				// Add new allocated datapoint to the vector
				// using copy constructor
				Datapoint *tmp = new Datapoint(*d);
				if (!tmp)
				{
					Logger::getLogger()->error("Failed to allocate datapoint for nested datapoint value in assignment operator");
					throw std::runtime_error("Failed to allocate datapoint for nested datapoint value in assignment operator");
				}
				m_value.dpa->push_back(tmp);
			}
			else
			{
				Logger::getLogger()->error("NULL datapoint found in nested data point value in copy constructor");
				throw std::runtime_error("NULL datapoint found in nested data point value in assignment operator");
			}
		}
		break;
	default:
		m_value = rhs.m_value;
		break;
	}

	return *this;
}

/**
 * Escape quotes etc to allow the string to be a property value within
 * a JSON document
 *
 * @param str	The string to escape
 * @return The escaped string
 */
const std::string DatapointValue::escape(const std::string& str) const
{
std::string rval;
int bscount = 0;

	for (size_t i = 0; i < str.length(); i++)
	{
		if (str[i] == '\\')
		{
			bscount++;
		}
		else if (str[i] == '\"')
		{
			if ((bscount & 1) == 0)	// not already escaped
			{
				rval += "\\";	// Add escape of "
			}
			bscount = 0;
		}
		else
		{
			bscount = 0;
		}
		rval += str[i];
	}
	return rval;
}
