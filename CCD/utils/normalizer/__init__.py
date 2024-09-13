#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from utils.parser import parser

global IDENTIFIERS
IDENTIFIERS = dict()

global SOLIDITY_LANGUAGE_KEYWORDS
SOLIDITY_LANGUAGE_KEYWORDS = ["selfdestruct", "assert", "require", "revert", "addmod", "mulmod", "keccak256", "sha3", "sha256", "ripemd160", "ecrecover", "this", "msg", "block", "_", "now"]

def clear_parser_identifiers():
    global IDENTIFIERS
    IDENTIFIERS = dict()

def normalize_child(child):
    global IDENTIFIERS

    if child == None:
        return ""

    if type(child) == str:
        return child

    if type(child) == list:
        for element in child:
            return normalize_child(element)

    if child.type == "PragmaDirective":
        return ""

    if child.type == "FileLevelConstant":
        return ""

    if child.type == "ContractDefinition":
        base = ""
        for i in range(len(child.baseContracts)):
            base_contract = child.baseContracts[i]
            if i == 0:
                base += " is "
            base_name = normalize_child(base_contract)
            if not base_name in IDENTIFIERS:
                IDENTIFIERS[base_name] = child.kind[0]
            base += IDENTIFIERS[base_name]
            if i < len(child.baseContracts) - 1:
                base += ","
        if not child.name in IDENTIFIERS:
            IDENTIFIERS[child.name] = child.kind[0]
        contract_definition = child.kind + " " + IDENTIFIERS[child.name] + base + "{"
        for sub_node in child.subNodes:
            contract_definition += normalize_child(sub_node)
        return contract_definition + "}"

    if child.type == "InheritanceSpecifier":
        return normalize_child(child.baseName)

    if child.type == "UserDefinedTypeName":
        return child.namePath

    if child.type == "FunctionDefinition":
        if "function()" in child.name:
            function_definition = "function fallback("
        elif child.name == "constructor" or child.name in IDENTIFIERS and IDENTIFIERS[child.name] == 'c':
            function_definition = "constructor("
        else:
            IDENTIFIERS[child.name] = "f"
            function_definition = "function " + IDENTIFIERS[child.name] + "("
        function_definition += normalize_child(child.parameters) + ")"
        for modifier in child.modifiers:
            function_definition += " " + normalize_child(modifier)
        if child.returnParameters:
            function_definition += "returns("
            function_definition += normalize_child(child.returnParameters)
            function_definition += ")"
        function_definition += "{"
        if child.body:
            for statement in child.body.statements:
                if type(statement) == list:
                    for element in statement:
                        if type(element) == str:
                            function_definition += element
                        else:
                            function_definition += normalize_child(element)
                else:
                    function_definition += normalize_child(statement)
        function_definition += "}"
        return function_definition

    if child.type == "FunctionCall":
        if type(child.expression) == list:
            function_call = ""
            for e in child.expression:
                if type(e) == list:
                    for e2 in e:
                        if type(e2) == parser.Node:
                            if "name" in e2 and e2.name not in IDENTIFIERS and e2.type == "Identifier" and e2.name not in SOLIDITY_LANGUAGE_KEYWORDS:
                                IDENTIFIERS[e2.name] = "f"
                            function_call += normalize_child(e2)
                        else:
                            function_call += str(e2)
                else:
                    if type(e) == parser.Node:
                        if "name" in e and e.name not in IDENTIFIERS and e.type == "Identifier" and e.name not in SOLIDITY_LANGUAGE_KEYWORDS:
                            IDENTIFIERS[e.name] = "f"
                        function_call += normalize_child(e)
                    else:
                        function_call += str(e)
            function_call += "("
        elif type(child.expression) == str:
            function_call = child.expression + "("
        else:
            if child.expression:
                if "name" in child.expression and child.expression.name not in IDENTIFIERS and child.expression.type == "Identifier" and child.expression.name not in SOLIDITY_LANGUAGE_KEYWORDS:
                    IDENTIFIERS[child.expression.name] = "f"
                function_call = normalize_child(child.expression) + "("
            else:
                function_call = "f("
        for i in range(len(child.arguments)):
            argument = child.arguments[i]
            if type(argument) == list:
                for arg in argument:
                    if type(arg) == parser.Node:
                        function_call += normalize_child(arg)
                    else:
                        function_call += str(arg)
            else:
                function_call += normalize_child(argument)
            if i < len(child.arguments) - 1:
                 function_call += ","
        function_call += ")"
        return function_call

    if child.type == "ModifierDefinition":
        if not child.name in IDENTIFIERS:
            IDENTIFIERS[child.name] = "m"
        modifier_definition = "modifier " + IDENTIFIERS[child.name] + "("
        if child.parameters:
            modifier_definition += normalize_child(child.parameters)
        modifier_definition += "){"
        if child.body and "statements" in child.body:
            for statement in child.body.statements:
                modifier_definition += normalize_child(statement)
        modifier_definition += "}"
        return modifier_definition

    if child.type == "ModifierInvocation":
        if not child.name in IDENTIFIERS:
            IDENTIFIERS[child.name] = "m"
        modifier_invocation = IDENTIFIERS[child.name] + "("
        for argument in child.arguments:
            modifier_invocation += normalize_child(argument)
        modifier_invocation += ")"
        return modifier_invocation

    if child.type == "VariableDeclarationStatement":
        variable_declaration = ""
        if child.variables:
            for variable in child.variables:
                if child.initialValue:
                    variable_declaration += normalize_child(variable) + "=" + normalize_child(child.initialValue) + ";"
                else:
                    variable_declaration += normalize_child(variable) + ";"
        elif not child.variables and child.initialValue:
            variable_declaration += normalize_child(child.initialValue) + ";"
        return variable_declaration

    if child.type == "StateVariableDeclaration":
        for variable in child.variables:
            normalize_child(variable)
        return ""

    if child.type == "VariableDeclaration":
        variable_name = child.name
        if not variable_name in IDENTIFIERS.keys():
            if "typeName" in child:
                IDENTIFIERS[variable_name] = normalize_child(child.typeName)
            else:
                IDENTIFIERS[variable_name] = "uint"
        return IDENTIFIERS[variable_name]

    if child.type == "IndexAccess":
        variable_name = normalize_child(child.base)
        if not variable_name in IDENTIFIERS.keys() and not variable_name in IDENTIFIERS.values():
            IDENTIFIERS[variable_name] = "mapping"
        if variable_name in IDENTIFIERS.keys():
            return IDENTIFIERS[variable_name] + "[" + normalize_child(child.index) + "]"
        return "mapping" + "[" + normalize_child(child.index) + "]"

    if child.type == "MemberAccess":
        expression = normalize_child(child.expression)
        if child.memberName == "call" and expression == "uint":
            expression = "address"
        return expression + "." + child.memberName

    if child.type in ["Identifier", "ElementaryTypeName"]:
        if child.name in SOLIDITY_LANGUAGE_KEYWORDS:
            return child.name
        if child.name in IDENTIFIERS:
            return IDENTIFIERS[child.name]
        if child.type == "Identifier":
            IDENTIFIERS[child.name] = "uint"
            return IDENTIFIERS[child.name]
        if child.type == "ElementaryTypeName":
            if child.name == "uint256":
                return "uint"
        return child.name

    if child.type == "ExpressionStatement":
        if type(child.expression) == list:
            expression_statement = ""
            for expression in child.expression:
                if type(expression) == parser.Node:
                    expression_statement += normalize_child(expression)
                else:
                    expression_statement += str(expression)
            return expression_statement + ";"
        else:
            return normalize_child(child.expression) + ";"

    if child.type == "IfStatement":
        true_body = child.TrueBody
        if type(true_body) == parser.Node:
            true_body = normalize_child(true_body)
        if child.FalseBody:
            false_body = child.FalseBody
            if type(false_body) == parser.Node:
                false_body = normalize_child(false_body)
            if true_body:
                return "if(" + normalize_child(child.condition) + "){" + true_body + "}else{" + false_body + "}"
            else:
                return "if(" + normalize_child(child.condition) + "){}else{" + false_body + "}"
        else:
            if true_body:
                return "if(" + normalize_child(child.condition) + "){" + true_body + "}"
            else:
                return "if(" + normalize_child(child.condition) + "){}"

    if child.type == "Block":
        block = ""
        for statement in child.statements:
            if type(statement) == list:
                for element in statement:
                    if type(element) == str:
                        block += element
                    else:
                        block += normalize_child(element)
            elif type(statement) == str:
                block += statement
            else:
                block += normalize_child(statement)
        return block

    if child.type == "BinaryOperation":
        left = ""
        if type(child.left) == list:
            for i in range(len(child.left)):
                c = child.left[i]
                if type(c) == parser.Node:
                    left += normalize_child(c)
                else:
                    left += str(c)
        else:
            left = normalize_child(child.left)
        right = ""
        if type(child.right) == list:
            for i in range(len(child.right)):
                c = child.right[i]
                if type(c) == parser.Node:
                    right += normalize_child(c)
                else:
                    right += str(c)
        else:
            right = normalize_child(child.right)
        return left + child.operator + right

    if child.type == "NumberLiteral":
        if child.subdenomination:
            return child.number + child.subdenomination
        return child.number

    if child.type == "stringLiteral":
        return "stringLiteral"

    if child.type == "EmitStatement":
        return "emit " + normalize_child(child.eventCall) + ";"

    if child.type == "TupleExpression":
        tuple_expression = "("
        for component in child.components:
            tuple_expression += normalize_child(component)
        tuple_expression += ")"
        return tuple_expression

    if child.type == "ArrayTypeName":
        array_name = normalize_child(child.baseTypeName) + "["
        if child.length:
            if type(child.length) == parser.Node:
                array_name += normalize_child(child.length)
            else:
                array_name += child.length
        array_name += "]"
        return array_name

    if child.type == "UnaryOperation":
        if child.isPrefix:
            return child.operator + normalize_child(child.subExpression)
        else:
            return normalize_child(child.subExpression) + child.operator

    if child.type == "BooleanLiteral":
        return str(child.value).lower()

    if child.type == "EnumDefinition":
        enum_definition = "enum " + child.name + "{"
        for i in range(len(child.members)):
            member = child.members[i]
            enum_definition += normalize_child(member)
            if i < len(child.members) - 1:
                enum_definition += ","
        enum_definition += "}"
        return enum_definition

    if child.type == "EnumValue":
        return child.name

    if child.type == "EventDefinition":
        IDENTIFIERS[child.name] = "e"
        return "event e(" + normalize_child(child.parameters) + ");"

    if child.type == "ParameterList":
        parameters = ""
        for i in range(len(child.parameters)):
            parameter = child.parameters[i]
            parameter_name = parameter.name
            if not parameter_name in IDENTIFIERS.keys():
                IDENTIFIERS[parameter_name] = normalize_child(parameter.typeName)
            parameters += IDENTIFIERS[parameter_name]
            if i < len(child.parameters) - 1:
                parameters += ","
        return parameters

    if child.type == "StructDefinition":
        struct_definition = "struct "
        struct_name = child.name
        if not struct_name in IDENTIFIERS.keys():
            IDENTIFIERS[struct_name] = "s"
        struct_definition += IDENTIFIERS[struct_name] + "{"
        for member in child.members:
            struct_definition += normalize_child(member) + ";"
        struct_definition += "}"
        return struct_definition

    if child.type == "Mapping":
        return "mapping(" + normalize_child(child.keyType) + "=>" + normalize_child(child.valueType) + ")"

    if child.type == "NewExpression":
        return "new " + normalize_child(child.typeName)

    if child.type == "ForStatement":
        return "for(" + normalize_child(child.initExpression) + normalize_child(child.conditionExpression) + ";" + normalize_child(child.loopExpression) + "){" + normalize_child(child.body) + "}"

    if child.type == "CustomErrorDefinition":
        return "error " + normalize_child(child.name) + "(" + normalize_child(child.parameterList) + ");"

    if child.type == "RevertStatement":
        return "revert " + normalize_child(child.functionCall) + ";"

    if child.type == "UsingForDeclaration":
        if type(child.typeName) == parser.Node:
            return "using " + child.libraryName + " for " + normalize_child(child.typeName) + ";"
        else:
            return "using " + str(child.libraryName) + " for " + str(child.typeName) + ";"

    if child.type == "Conditional":
        return normalize_child(child.condition) + "?" + normalize_child(child.TrueExpression) + ":" + normalize_child(child.FalseExpression) + ";"

    if child.type == "WhileStatement":
        return "while(" + normalize_child(child.condition) + "){" + normalize_child(child.body) + "}"

    if child.type == "ImportDirective":
        return ""

    if child.type == "ThrowStatement":
        return "throw;"

    if child.type == "hexLiteral":
        return child.value

    if child.type == "TryStatement":
        try_statement = "try " + normalize_child(child.expression) + "returns(" + normalize_child(child.returnParameters) + "){" + normalize_child(child.block) + "}"
        for clause in child.catchClause:
            try_statement += normalize_child(clause)
        return try_statement

    if child.type == "CatchClause":
        catch_clause = "catch " + normalize_child(child.identifier) + "(" + normalize_child(child.parameterList) + "){" + normalize_child(child.block) + "}"
        return catch_clause

    if child.type == "UncheckedStatement":
        return "unchecked{" + normalize_child(child.body) + "}"

    if child.type == "FunctionTypeName":
        return ""

    if child.type == "InLineAssemblyStatement":
        return ""

    if child.type == "DoWhileStatement":
        return "do{" + normalize_child(child.body) + "}while(" + normalize_child(child.condition) + ");"

    else:
        print("Unknown type", child.type)
        import pprint
        pprint.pprint(child)
        raise Exception("Unknown type: "+str(child.type))
