define(["js/models/settings/course_grader"], CourseGrader =>
    describe("CourseGraderModel", () =>
        describe("parseWeight", function() {
            it("converts a float to an integer", function() {
                const model = new CourseGrader({weight: 7.0001, min_count: 3.67, drop_count: 1.88}, {parse:true});
                expect(model.get('weight')).toBe(7);
                expect(model.get('min_count')).toBe(4);
                expect(model.get('drop_count')).toBe(2);
            });

            it("converts float value of weight to an integer with rounding", function() {
                const model = new CourseGrader({weight:  28.999999999999996}, {parse:true});
                expect(model.get('weight')).toBe(29);
            });

            it("converts a string to an integer", function() {
                const model = new CourseGrader({weight: '7.0001', min_count: '3.67', drop_count: '1.88'}, {parse:true});
                expect(model.get('weight')).toBe(7);
                expect(model.get('min_count')).toBe(4);
                expect(model.get('drop_count')).toBe(2);
            });

            it("does a no-op for integers", function() {
                const model = new CourseGrader({weight: 7, min_count: 3, drop_count: 1}, {parse:true});
                expect(model.get('weight')).toBe(7);
                expect(model.get('min_count')).toBe(3);
                expect(model.get('drop_count')).toBe(1);
            });

            it("gives validation error if min_count is less than 1 or drop_count is NaN", function() {
                const model = new CourseGrader();
                let errors = model.validate({min_count: 0, drop_count: ''}, {validate:true});
                expect(errors.min_count).toBe('Please enter an integer greater than 0.');
                expect(errors.drop_count).toBe('Please enter non-negative integer.');
                // don't allow negative integers
                errors = model.validate({min_count: -12, drop_count: -1}, {validate:true});
                expect(errors.min_count).toBe('Please enter an integer greater than 0.');
                expect(errors.drop_count).toBe('Please enter non-negative integer.');
                // don't allow floats
                errors = model.validate({min_count: 12.2, drop_count: 1.5}, {validate:true});
                expect(errors.min_count).toBe('Please enter an integer greater than 0.');
                expect(errors.drop_count).toBe('Please enter non-negative integer.');
            });

            it("gives validation error if drop_count is not less than min_count", function() {
                const model = new CourseGrader();
                const type = 'Homework'
                let errors = model.validate({min_count: 3, drop_count: 2, type: type}, {validate:true});
                expect(errors).toBeUndefined();

                errors = model.validate({min_count: 3, drop_count: 3, type: type}, {validate:true});
                expect(errors.min_count).toBeUndefined();
                expect(errors.drop_count).toBe('You must have at least one undroppable Homework assignment.');

                errors = model.validate({min_count: 3, drop_count: 4, type: type}, {validate:true});
                expect(errors.min_count).toBeUndefined();
                expect(errors.drop_count).toBe('You must have at least one undroppable Homework assignment.');
            });
        })
    )
);

