from a2a_servers.common.types import (JSONRPCResponse, ContentTypeNotSupportedError, UnsupportedOperationError,)
from typing import List

# kiểm tra độ tương thích các chế độ đầu ra của client và server
# đảm bảo server có thể trả về dữ liệu ở định dạng mà client chấp nhận
#  --> Modalities are compatible if they are both non-empty and there is at least one common element.
def are_modalities_compatible(server_output_modes: List[str], client_output_modes: List[str]):
    if client_output_modes is None or len(client_output_modes) == 0:
        return True # --> Client không chỉ định định dạng, nghĩa là chấp nhận bất kỳ định dạng nào từ server.
    if server_output_modes is None or len(server_output_modes) == 0:
        return True # --> Server không chỉ định định dạng, nghĩa là có thể đáp ứng bất kỳ yêu cầu nào từ client
    return any(x in server_output_modes for x in client_output_modes) # --> Trả về True nếu tìm thấy ít nhất một phần tử chung, False nếu không.

# 2 hàm dưới dùng để tạo các phản hồi JSON-RPC chứa lỗi khi xảy ra vấn đề về loại nội dung (ContentTypeNotSupportedError) hoặc thao tác không được hỗ trợ (UnsupportedOperationError).
# VD: client yêu cầu định dạng image/jpeg nhưng server chỉ hỗ trợ text.
def new_incompatible_types_error(request_id): 
    return JSONRPCResponse(id=request_id, error=ContentTypeNotSupportedError())

def new_not_implemented_error(request_id):
    return JSONRPCResponse(id=request_id, error=UnsupportedOperationError())