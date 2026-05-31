

$(document).ready(function () {
	$(".opener").click(function () {

		var fileLink = $(this).attr('id');
		// alert(fileLink);
		var formData = {
			"program": fileLink
		};
		$.ajax({
			type: "POST",
			//url 	: "http://zabgu.ru/php/../educational_parser_utilities.php",
			url: "./educational_parser_utilities.php",
			data: formData,

			success: function (gettingData) {
				var result = JSON.parse(gettingData);
				var elements = '';
				if (result.answer === "success") {
					$(result.links).each(function () {
						var elementName = $(this).attr('hrefs').split("/");
						if ($(this).attr('hrefs').indexOf('.sig') != -1) {
							elements += '(<a class="" target="_Blank" href="' + $(this).attr('hrefs') + '">' + elementName[elementName.length - 1] + '</a>)</br>';
						} else {
							elements += '<a class="" target="_Blank" href="' + $(this).attr('hrefs') + '">' + elementName[elementName.length - 1] + '</a></br>';
						}
					});
					$('#dialog').html(elements);
				}
			}

		});

	});

	$(".program_practice_opener").click(function () {
		var folderLink = $(this).attr('id');
		//alert(folderLink);
		var formData = {
			"year_program": folderLink
		};
		$.ajax({
			type: "POST",
			// url		: 	"http://zabgu.ru/php/../educational_parser_utilities.php",
			url: "./educational_parser_utilities.php",
			data: formData,

			success: function (gettingData) {
				var result = JSON.parse(gettingData);
				var elements = '';
				if (result.answer === "success") {

					$(result.links).each(function () {
						var elementName = $(this).attr('hrefs').split("/");
						if ($(this).attr('hrefs').indexOf('.sig') != -1) {
							elements += '(<a class="" target="_Blank" href="' + $(this).attr('hrefs') + '">' + elementName[elementName.length - 1] + '</a>)</br>';
						} else {
							elements += '<a class="" target="_Blank" href="' + $(this).attr('hrefs') + '">' + elementName[elementName.length - 1] + '</a></br>';
						}
					});
					$('#program_practice_modal').html(elements);
				}
			}
		});
	});

	$(".educational_plan_opener").click(function () {
		var folderLink = $(this).attr('id');
		// alert(folderLink);
		var formData = {
			"year_plan": folderLink
		};
		$.ajax({
			type: "POST",
			// url		: 	"http://zabgu.ru/php/../educational_parser_utilities.php",
			url: "./educational_parser_utilities.php",
			data: formData,

			success: function (gettingData) {
				var result = JSON.parse(gettingData);
				var elements = '';
				if (result.answer === "success") {

					$(result.links).each(function () {
						var elementName = $(this).attr('hrefs').split("/");
						if ($(this).attr('hrefs').indexOf('.sig') != -1) {
							elements += '(<a class="" target="_Blank" href="' + $(this).attr('hrefs') + '">' + elementName[elementName.length - 1] + '</a>)</br>';
						} else {
							elements += '<a class="" target="_Blank" href="' + $(this).attr('hrefs') + '">' + elementName[elementName.length - 1] + '</a></br>';
						}
					});
					$('#educational_plan_modal').html(elements);
				}
			}
		});
	});

	// Модальное окно с методическими и иными документами для лицея
	$(".liceum_methodology").click(function () {
		//console.log("click");
		var folderLink = $(this).attr('id');
		// console.log(folderLink);
		var formData = {
			"methodology": folderLink
		};
		console.log(formData);
		$.ajax({
			type: "POST",
			url: "./liceum_programs_manager.php",
			data: formData,

			success: function (gettingData) {
				// alert(gettingData);
				var result = JSON.parse(gettingData);

				var elements = '';
				if (result.answer === "success") {
					// alert(result.links);
					$(result.links).each(function () {
						var elementName = $(this).attr('hrefs').split("/");
						if ($(this).attr('hrefs').indexOf('.sig') != -1) {
							elements += '(<a class="" target="_Blank" href="' + $(this).attr('hrefs') + '">' + elementName[elementName.length - 1] + '</a>)</br>';
						} else {
							elements += '<a class="" target="_Blank" href="' + $(this).attr('hrefs') + '">' + elementName[elementName.length - 1] + '</a></br>';
						}
					});
					$('#liceum_methodology_modal').html(elements);
				}
			},
			error: function () {
				console.log('ajax query error!!!');
			}
		});
	});

	$(".working_programs").click(function () {
		var formData = {
			"year": $(this).data('year'),
			"speciality": $(this).data('speciality'),
			"profile": $(this).data('profile')
		};
		$('#working_programs_modal').html('');
		$.ajax({
			type: "POST",
			url: "./educational_parser_utilities.php",
			data: formData,

			success: function (gettingData) {
				var result = JSON.parse(gettingData);
				var elements = '';
				if (result.answer === "success") {
					let baseUrl = "https://eos.zabgu.ru/local/working_program/modules/typical_programs/PDF/PDF.php?id=";

					if (result.links[0].length == 0 && result.links[1].length == 0 && result.links[2].length == 0) {
						elements += "<span style='font-weight: bold'>Рабочие программы не найдены<span><br>";
					} else {
						if (result.links[0].length) {
							elements += "<span style='font-weight: bold'>Очная:<span><br>";
							$(result.links[0]).each(function (index, wp_link) {
								elements += '<a class="" target="_blank" href="' + baseUrl + wp_link.id + '">' + wp_link.label + '</a></br>';
							});
						}
						if (result.links[1].length) {
							elements += "<br><span style='font-weight: bold'>Заочная:<span><br>";
							$(result.links[1]).each(function (index, wp_link) {
								elements += '<a class="" target="_blank" href="' + baseUrl + wp_link.id + '">' + wp_link.label + '</a></br>';
							});
						}
						if (result.links[2].length) {
							elements += "<br><span style='font-weight: bold'>Очно-заочная:<span><br>";
							$(result.links[2]).each(function (index, wp_link) {
								elements += '<a class="" target="_blank" href="' + baseUrl + wp_link.id + '">' + wp_link.label + '</a></br>';
							});
						}
					}
					$('#working_programs_modal').html(elements);
				}
			}
		});
	});

	document.querySelectorAll(".spo_working_programs").forEach(
		function (link) {
			link.addEventListener(
				"click",
				function (event) {
					console.log(event.target.parent);
					console.log(event.target.parentNode.children[1]);
					let html = event.target.parentNode.children[1].innerHTML;
					document.querySelector("#spo_working_programs_modal").innerHTML = html;
				}
			)
		}
	)
	
	$(function () {
		var dialogOptions = {
			autoOpen: false,
			show: {
				effect: "blind",
				duration: 1000
			},
			hide: {
				effect: "explode",
				duration: 1000
			}
		};
		$('.educational_plan_opener').click(function () {
			$('#educational_plan_modal').dialog(dialogOptions).dialog('open');
		});

		$('.program_practice_opener').click(function () {
			$('#program_practice_modal').dialog(dialogOptions).dialog('open');
		});

		$('.opener').click(function () {
			$('#dialog').dialog(dialogOptions).dialog('open');
		});

		$('.liceum_methodology').click(function () {
			$('#liceum_methodology_modal').dialog(dialogOptions).dialog('open');
		});
		var wpDialogOptions = {
			autoOpen: false,
			show: {
				effect: "blind",
				duration: 1000
			},
			hide: {
				effect: "explode",
				duration: 1000
			},
			maxHeight: 500,
			width: 500
		};

		$('.working_programs').click(function () {
			$('#working_programs_modal').dialog(wpDialogOptions).dialog('open');
		});

		$('.spo_working_programs').click(function () {
			$('#spo_working_programs_modal').dialog(wpDialogOptions).dialog('open');
		});

	});

});
$(document).scroll(function () {
	$('.learning_program_table_fixed_cell').css({
		left: $(document).scrollLeft()
	});

});