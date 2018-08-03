$(document).ready(function(){

  $("li[title]").click(function() {
    var toolTip = $(this).find(".command-tooltip");
    if (!toolTip.length) {
      $("li[title]").not($(this)).children().remove();
      $(this).append("<span class='command-tooltip'>" + $(this).attr("title") + "<br>Times used: " + $(this).attr("data-times-used") + "</span>");
    } else {
      toolTip.remove();
    }
  });

  $('#search').bind('keyup', function() {
    var input = $(this).val().toUpperCase();
    $("#user-command-list li").each(function(index, value) {
      var command = $(value).text().toUpperCase();
      var desc = $(value).attr("title").toUpperCase();
      if (command.indexOf(input) > -1 || desc.indexOf(input) > -1) {
          $(value).show();
      } else {
          $(value).hide();
      }
    });
  });

  $("a[info-panel]").click(function() {
    $("a[info-panel]").not($(this)).removeClass("active");
    $(this).addClass("active");
    var infoPanel = $($(this).attr("info-panel"));
    infoPanel.show();
    $("div[info-panel]").not(infoPanel).hide();
    $("body").scrollTop(0);
  });

  $("#sort-used").click(function() {
    $("#user-command-list li").sort(function(a, b) {
      return parseInt($(a).attr("data-times-used")) < parseInt($(b).attr("data-times-used")) ? 1 : -1;
    }).prependTo($("#user-command-list"));
  });
});
