$(document).ready(function() {
    $(".submit_search").on("click", runSearch);
});

var modalId = -1
var commentModal = $('#modal-comment');
var deleteModal = $('#modal-delete');
var reindexModal = $('#modal-reindex');

function showDeleteModal(id) {
    deleteModal.css("display","block");
    modalId = id;
}

function showCommentModal(id) {
    commentModal.css("display","block");
    modalId = id;
}

function showReindexModal() {
    reindexModal.css("display","block");
}

function hideModal(){
    commentModal.css("display","none");
    deleteModal.css("display","none");
    reindexModal.css("display","none");
    modalId = -1;
}

function deleteResult(){
    var idToDelete = modalId.toString();
    var deleteUrl = ["delete/", idToDelete].join("");
    hideModal();
    $.post(deleteUrl).done(function(response, err){
        alert((response === 0) ? "Successfully deleted " + idToDelete : "Deletion Error");
    });
}

function reindex(){
    hideModal()
    $.post("/reindex").done(function(response, err){
        alert((response === 0) ? "Successfully reindexed data " : "Error reindexing");
    });
}

function commentResult(deleteComment){
    var commentText = ''
    if (!deleteComment) {
        commentText = $('#comment-text').val();
    }
    var idToComment = modalId;
    var commentUrl = "comment/solr/" + idToComment.toString() + "/" + commentText;
    hideModal();
    $.post(commentUrl).done(function(response, err){
        if (!deleteComment) {
            alert((response === 0) ? "Commented '" + commentText + "' to document number " + idToComment : "Commenting Error");
        }
        else {
            alert((response === 0) ? "Deleted comment" : "Comment Deletion Error");
        }

    });
}

function runSearch() {
    var results = $("#query-results").html("");
    var searchText = $("#search_text").val();
    var numberResults = $("span#num_results");

    if (searchText === "") {
        alert('mandatory field not populated');
        return false;
    }
    var query = '';
    var searchCategory = $("#fields").val();
    var company = $("#companies").val();
    if (searchCategory === 'both'){
        query = addFilter("or", query, 'Question', searchText);
        query = addFilter("or", query, 'Response', searchText);
    }
    else {
        query = addFilter("or", query, searchCategory, searchText);
    }
    query = addFilter("and", query,"Company", company);
    $.post("query/" + query).done(function(response, err){
        numberResults.html(response['num_found']);
        results.html(response['html']);
    });
}

function addFilter(operator, query, field, value) {
    if (operator === 'and'){
        var operatorText = '%20AND%20';
    }
    else
        var operatorText = '%20OR%20'
    if (query === "") {
        return [field, ':', value].join("");
    }
    return (value === "") ? query : [query, operatorText, field, ':', value].join("");
}

$(document).ready(function(){
    $(document).keypress(function(e){
        if(e.which === 13) {
            if (commentModal.css("display") == "block") {
                commentResult(false)
            }
            else if (deleteModal.css("display") == "block") {
                deleteResult()
            }
            else if (reindexModal.css("display") == "block") {
                reindex()
            }
            else{
                runSearch()
            }
        }
    });
});
