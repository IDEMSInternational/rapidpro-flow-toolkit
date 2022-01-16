from typing import List
from parsers.common.rowparser import ParserModel
from pydantic import Field


class Result(ParserModel):
    variable: str = ''
    value: str = ''

class Message(ParserModel):
    text: str = ''
    attachment: str = '' # TODO: Consider supporting multiple attachments

class RowData(ParserModel):
    flow_name: str
    result: Result
    main_messages: List[Message]
    interaction_message: Message
    already_received_message: Message
    no_messages: List[Message]
    extra_messages: List[Message]

    def header_name_to_field_name_with_context(header, row):
        # TODO: This should be defined outside of this function
        basic_header_dict = {
            "core_content_flow" : "flow_name",
            "result_list" : "result",
            "message_text_list" : "main_messages:*:text",
            "attachment_list" : "main_messages:*:attachment",
            "interaction_message" : "interaction_message:text",
            "interaction_attachment" : "interaction_message:attachment",
            "already_received_interaction" : "already_received_message:text",
            "already_received_attachment" : "already_received_message:attachment",
            "no_message_list" : "no_messages:*:text",
            "extra_message_list" : "extra_messages:*:text",
        }
        
        return basic_header_dict.get(header, header)
